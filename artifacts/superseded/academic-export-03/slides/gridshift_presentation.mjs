import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const [contentPath, buildDirectory, finalPptxPath, pdfPath, renderDirectory, workspaceDirectory] =
  process.argv.slice(2);

if (![contentPath, buildDirectory, finalPptxPath, pdfPath, renderDirectory, workspaceDirectory].every(Boolean)) {
  throw new Error("Usage: presentation.mjs CONTENT BUILD_DIR FINAL_PPTX PDF RENDER_DIR WORKSPACE_DIR");
}

const nodeModules = process.env.RUNTIME_NODE_MODULES;
const skillDirectory = process.env.GRIDSHIFT_PRESENTATIONS_SKILL;
const pythonExecutable = process.env.RUNTIME_PYTHON;
if (!nodeModules || !skillDirectory || !pythonExecutable) {
  throw new Error("RUNTIME_NODE_MODULES, GRIDSHIFT_PRESENTATIONS_SKILL, and RUNTIME_PYTHON are required");
}

const packageRequire = createRequire(path.join(nodeModules, "__gridshift_bootstrap__.cjs"));
const artifactToolUrl = pathToFileURL(packageRequire.resolve("@oai/artifact-tool")).href;
const artifactTool = await import(artifactToolUrl);
const { FileBlob, Presentation, PresentationFile } = artifactTool;
const utilityUrl = pathToFileURL(path.join(skillDirectory, "container_tools", "artifact_tool_utils.mjs")).href;
const {
  applyPresentationChartFont,
  finalizePresentation,
  makeNativeBulletParagraphs,
  resolvePresentationFont,
} = await import(utilityUrl);

const palette = {
  ink: "#1E302F",
  green: "#176B66",
  teal: "#127C74",
  coral: "#C75F45",
  blue: "#466A83",
  gray: "#536468",
  light: "#E9EFED",
  white: "#FFFFFF",
  grid: "#CED8D5",
};
const fontFamily = resolvePresentationFont();
const content = JSON.parse(await fs.readFile(contentPath, "utf8"));
if (!Array.isArray(content.slides) || content.slides.length !== 12) {
  throw new Error(`Expected 12 content slides, got ${content.slides?.length ?? "none"}`);
}
if (content.slides.some((slide) => typeof slide.notes !== "string" || !slide.notes.trim())) {
  throw new Error("Every slide must have non-empty speaker notes");
}

await fs.mkdir(buildDirectory, { recursive: true });
await fs.mkdir(path.dirname(finalPptxPath), { recursive: true });
await fs.mkdir(path.dirname(pdfPath), { recursive: true });
await fs.mkdir(renderDirectory, { recursive: true });

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const tableOwnerSlides = [];
const chartOwnerSlides = [];

function addText(slide, name, text, position, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position,
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: fontFamily,
    fontSize: 24,
    color: palette.ink,
    alignment: "left",
    ...style,
  };
  shape.text.insets = 0;
  return shape;
}

function addBullets(slide, bullets, position, name) {
  if (!Array.isArray(bullets) || bullets.length === 0) return;
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position,
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = makeNativeBulletParagraphs(bullets, {
    marginLeftPoints: 20,
    hangingPoints: 10,
    spaceAfterPoints: 7,
  });
  shape.text.style = {
    typeface: fontFamily,
    fontSize: 23,
    color: palette.ink,
  };
  shape.text.insets = 0;
}

function addTable(slide, tableData, position, slideNumber) {
  const headers = tableData.headers;
  const rows = tableData.rows;
  if (!Array.isArray(headers) || headers.length === 0 || !Array.isArray(rows)) {
    throw new Error(`Slide ${slideNumber} has an invalid table`);
  }
  const values = [headers, ...rows];
  const table = slide.tables.add({
    rows: values.length,
    columns: headers.length,
    left: position.left,
    top: position.top,
    width: position.width,
    height: position.height,
    columnWidths: headers.map((header, index) =>
      headers.length === 1 ? position.width :
      index === 0 && headers.length <= 3 ? position.width * 0.55 :
      headers.length <= 3 ? position.width * 0.45 / (headers.length - 1) :
      position.width / headers.length),
    values,
  });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: palette.grid, width: 0.8 });
  const body = table.cells.block({
    row: 0,
    column: 0,
    rowCount: values.length,
    columnCount: headers.length,
  });
  body.textStyle.fontSize = headers.length > 6 ? 14 : 16;
  body.textStyle.color = palette.ink;
  const header = table.cells.block({
    row: 0,
    column: 0,
    rowCount: 1,
    columnCount: headers.length,
  });
  header.fill = palette.green;
  header.textStyle.fontSize = 15;
  header.textStyle.color = palette.white;
  header.textStyle.bold = true;
  for (let row = 0; row < values.length; row += 1) {
    table.rows[row].height = position.height / values.length;
    for (let column = 0; column < headers.length; column += 1) {
      table.getCell(row, column).text.style = {
        typeface: fontFamily,
        fontSize: headers.length > 5 ? 18 : 21,
        color: row === 0 ? palette.white : palette.ink,
        bold: row === 0,
      };
    }
  }
  tableOwnerSlides.push(slideNumber);
  return table;
}

function addChart(slide, chartData, position, slideNumber) {
  if (!chartData || !Array.isArray(chartData.categories) || chartData.categories.length === 0) {
    return false;
  }
  const series = (chartData.series ?? [])
    .filter((item) => Array.isArray(item.values) && item.values.length === chartData.categories.length)
    .map((item, index) => ({
      name: item.name,
      values: item.values,
      fill: item.color ?? [palette.coral, palette.teal, palette.blue][index % 3],
      line: {
        style: "solid",
        fill: item.color ?? [palette.coral, palette.teal, palette.blue][index % 3],
        width: 3,
      },
      marker: { symbol: "circle", size: 5 },
    }));
  if (series.length === 0) return false;
  const isBar = chartData.type === "bar";
  const chart = slide.charts.add(isBar ? "bar" : "line", {
    position,
    title: chartData.title,
    titlePlacement: "aboveChart",
    titleTextStyle: { fontSize: 22, fill: palette.ink, bold: true },
    categories: chartData.categories,
    series,
    hasLegend: series.length > 1,
    legend: {
      position: "bottom",
      overlay: false,
      textStyle: { fontSize: 15, fill: palette.ink },
    },
    ...(isBar
      ? { barOptions: { direction: "column", grouping: "clustered", gapWidth: 55 } }
      : { lineOptions: { grouping: "standard", smooth: false } }),
    xAxis: {
      textStyle: { fontSize: 15, fill: palette.ink },
      majorGridlines: null,
      line: { style: "solid", fill: palette.grid, width: 1 },
    },
    yAxis: {
      title: { text: chartData.axis_title, textStyle: { fontSize: 16, fill: palette.ink } },
      textStyle: { fontSize: 14, fill: palette.ink },
      numberFormatCode: chartData.number_format_code ?? "#,##0.0",
      ...(chartData.y_min !== undefined ? { min: chartData.y_min } : {}),
      ...(chartData.y_max !== undefined ? { max: chartData.y_max } : {}),
      majorGridlines: { style: "solid", fill: palette.light, width: 1 },
      line: { style: "solid", fill: palette.grid, width: 1 },
    },
    dataLabels: { showValue: false },
    chartFill: palette.white,
    plotAreaFill: palette.white,
  });
  applyPresentationChartFont(chart, { fontFamily });
  chartOwnerSlides.push(slideNumber);
  return true;
}

async function addFigure(slide, figure, position) {
  if (!figure?.path) return false;
  const bytes = await fs.readFile(figure.path);
  slide.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png",
    alt: figure.alt ?? "Research diagnostic figure",
    fit: "contain",
    position,
  });
  return true;
}

for (const [index, item] of content.slides.entries()) {
  const slideNumber = index + 1;
  const slide = presentation.slides.add();
  slide.background.fill = palette.white;
  slide.speakerNotes.text = item.notes;
  slide.speakerNotes.setVisible(true);

  const titleTop = index === 0 ? 88 : 42;
  const titleHeight = index === 0 ? 88 : 70;
  const titleWidth = index === 0 ? 610 : 1136;
  addText(
    slide,
    `slide-${slideNumber}-title`,
    item.title,
    { left: 72, top: titleTop, width: titleWidth, height: titleHeight },
    { fontSize: index === 0 ? 72 : 56, bold: true, color: palette.green },
  );
  if (item.subtitle) {
    addText(
      slide,
      `slide-${slideNumber}-subtitle`,
      item.subtitle,
      { left: 76, top: 180, width: 585, height: 112 },
      { fontSize: 28, color: palette.gray },
    );
  }

  const hasTable = Boolean(item.table);
  const hasChart = Boolean(item.chart);
  const hasFigure = Boolean(item.figure);
  if (index === 0) {
    addBullets(
      slide,
      item.bullets,
      { left: 78, top: 330, width: 570, height: 160 },
      `slide-${slideNumber}-bullets`,
    );
    if (hasFigure) {
      await addFigure(slide, item.figure, { left: 710, top: 105, width: 500, height: 500 });
      addText(
        slide,
        `slide-${slideNumber}-caption`,
        "Development observations",
        { left: 720, top: 620, width: 480, height: 26 },
        { fontSize: 17, color: palette.gray },
      );
    }
  } else if (hasChart && hasTable) {
    addBullets(
      slide,
      item.bullets,
      { left: 78, top: 130, width: 1125, height: 98 },
      `slide-${slideNumber}-bullets`,
    );
    addChart(
      slide,
      item.chart,
      { left: 72, top: 245, width: 690, height: 405 },
      slideNumber,
    );
    addTable(
      slide,
      item.table,
      { left: 790, top: 250, width: 418, height: 390 },
      slideNumber,
    );
  } else if (hasFigure && hasTable) {
    addBullets(
      slide,
      item.bullets,
      { left: 78, top: 130, width: 1125, height: 88 },
      `slide-${slideNumber}-bullets`,
    );
    addTable(
      slide,
      item.table,
      { left: 72, top: 238, width: 500, height: 395 },
      slideNumber,
    );
    await addFigure(slide, item.figure, { left: 615, top: 260, width: 593, height: 340 });
  } else if (hasChart) {
    addBullets(
      slide,
      item.bullets,
      { left: 78, top: 132, width: 1120, height: 96 },
      `slide-${slideNumber}-bullets`,
    );
    addChart(
      slide,
      item.chart,
      { left: 72, top: 240, width: 1136, height: 410 },
      slideNumber,
    );
    if (hasTable) {
      addTable(slide, item.table, { left: 72, top: 540, width: 1136, height: 110 }, slideNumber);
    }
  } else if (hasFigure) {
    await addFigure(slide, item.figure, { left: 72, top: 245, width: 720, height: 410 });
    addBullets(
      slide,
      item.bullets,
      { left: 830, top: 248, width: 378, height: 385 },
      `slide-${slideNumber}-bullets`,
    );
    addText(
      slide,
      `slide-${slideNumber}-caption`,
      item.figure.alt ?? "Stored diagnostic figure",
      { left: 82, top: 658, width: 690, height: 23 },
      { fontSize: 16, color: palette.gray },
    );
  } else if (hasTable) {
    const denseBullets = (item.bullets?.length ?? 0) >= 4;
    addBullets(
      slide,
      item.bullets,
      { left: 78, top: 130, width: 1120, height: denseBullets ? 145 : 100 },
      `slide-${slideNumber}-bullets`,
    );
    addTable(
      slide,
      item.table,
      { left: 72, top: denseBullets ? 290 : 245, width: 1136, height: denseBullets ? 345 : 390 },
      slideNumber,
    );
  } else {
    addBullets(
      slide,
      item.bullets,
      { left: 86, top: 174, width: 1080, height: 450 },
      `slide-${slideNumber}-bullets`,
    );
  }

  if (item.subtitle && index !== 0) {
    addText(
      slide,
      `slide-${slideNumber}-subtitle`,
      item.subtitle,
      { left: 78, top: 112, width: 1120, height: 32 },
      { fontSize: 22, color: palette.gray },
    );
  }
}

const candidatePath = path.join(buildDirectory, "gridshift-presentation-candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const integrityValidatorPath = path.join(
  skillDirectory,
  "container_tools",
  "inspect_presentation_package_integrity.py",
);
const layoutValidatorPath = path.join(
  skillDirectory,
  "container_tools",
  "inspect_presentation_layout_geometry.py",
);
const layoutArgs = [
  "--expected-slide-size-emu",
  "12192000,6858000",
  "--validate-bullet-geometry",
  "--validate-heading-fit",
  ...tableOwnerSlides.flatMap((number) => ["--require-native-table-slide", String(number)]),
];
const receiptPath = path.join(buildDirectory, "validation", "presentation.validation.json");
await fs.mkdir(path.dirname(receiptPath), { recursive: true });
const finalized = await finalizePresentation({
  explicitTotalSlideCount: 12,
  requiredNativeTableOwnerSlides: tableOwnerSlides,
  requiredNativeChartOwnerSlides: chartOwnerSlides,
  nativeChartTargetApplication: "powerpoint",
  materializeLiteralChartWorkbooks: true,
  workspaceDir: workspaceDirectory,
  candidatePath,
  finalPath: finalPptxPath,
  pythonExecutable,
  integrityValidatorPath,
  layoutValidatorPath,
  layoutArgs,
  fontPolicy: { basis: "design", families: [fontFamily] },
  verifyArtifactToolImport: true,
  receiptPath,
});

const finalizedDeck = await PresentationFile.importPptx(await FileBlob.load(finalPptxPath));
if (finalizedDeck.slides.items.length !== 12) {
  throw new Error(`Finalized PPTX has ${finalizedDeck.slides.items.length} slides`);
}
for (const [index, slide] of finalizedDeck.slides.items.entries()) {
  const image = await finalizedDeck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(
    path.join(renderDirectory, `slide-${String(index + 1).padStart(2, "0")}.png`),
    new Uint8Array(await image.arrayBuffer()),
  );
}
console.log(JSON.stringify({
  finalPptxPath: finalized.finalPath,
  receiptPath: finalized.receiptPath,
  slideCount: finalizedDeck.slides.items.length,
  tableOwnerSlides,
  chartOwnerSlides,
  fontFamily,
}));
