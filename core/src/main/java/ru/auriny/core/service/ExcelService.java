package ru.auriny.core.service;

import com.github.pjfanning.xlsx.StreamingReader;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.streaming.SXSSFSheet;
import org.apache.poi.xssf.streaming.SXSSFWorkbook;
import org.apache.poi.xwpf.usermodel.ParagraphAlignment;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import ru.auriny.core.dto.AnalyzeTaskBatch;
import ru.auriny.core.dto.FinalReportRow;
import ru.auriny.core.dto.IncidentRow;
import ru.auriny.core.dto.ReportResult;
import ru.auriny.core.util.RedisKeys;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

@Slf4j
@Service
@RequiredArgsConstructor
public class ExcelService {
    private final AiQueueService aiQueueService;
    private static final int BATCH_SIZE = 50;

    public ReportResult processAndGenerateReport(MultipartFile file) throws IOException {
        log.info("Началась обработка файла: {}", file.getOriginalFilename());

        try (InputStream is = file.getInputStream();
             Workbook readWorkbook = StreamingReader.builder()
                     .rowCacheSize(100)
                     .bufferSize(4096)
                     .open(is)) {

            Sheet sheet = readWorkbook.getSheetAt(0);
            boolean isHeader = true;
            List<IncidentRow> batch = new ArrayList<>();

            for (Row row : sheet) {
                if (isHeader) {
                    isHeader = false;
                    continue;
                }

                String topicGroup = getCellAsString(row, 19);
                String district = getCellAsString(row, 22);
                String text = getCellAsString(row, 34);

                if (text == null || text.isBlank()) continue;

                batch.add(new IncidentRow(district, topicGroup, text));
                if (batch.size() >= BATCH_SIZE) {
                    aiQueueService.pushTask(RedisKeys.QUEUE_TASKS, new AnalyzeTaskBatch(false, new ArrayList<>(batch)));
                    batch.clear();
                }
            }

            if (!batch.isEmpty()) aiQueueService.pushTask(RedisKeys.QUEUE_TASKS, new AnalyzeTaskBatch(false, batch));

            log.info("Чтение файла завершено. Отправляем isLastBatch = true");
            aiQueueService.pushTask(RedisKeys.QUEUE_TASKS, new AnalyzeTaskBatch(true, List.of()));
        }

        log.info("Ждем генерации саммари...");
        FinalReportRow[] results = aiQueueService.waitForResult(RedisKeys.QUEUE_RESULTS, FinalReportRow[].class, 1200);
        String grandSummary = aiQueueService.waitForResult(RedisKeys.QUEUE_SUMMARY, String.class, 1200);

        if (results == null || results.length == 0 || grandSummary == null) {
            throw new RuntimeException("Не удалось получить результат от AI-модуля (таймаут или ошибка)");
        }

        byte[] top3ExcelBytes;
        byte[] top10ExcelBytes;

        try (SXSSFWorkbook top3Workbook = new SXSSFWorkbook(100);
             SXSSFWorkbook top10Workbook = new SXSSFWorkbook(100);
             ByteArrayOutputStream bosTop3 = new ByteArrayOutputStream();
             ByteArrayOutputStream bosTop10 = new ByteArrayOutputStream()) {

            SXSSFSheet top3Sheet = top3Workbook.createSheet("Топ3 критичные");
            SXSSFSheet top10Sheet = top10Workbook.createSheet("Топ10 общий список");

            CellStyle top3HeaderStyle = createHeaderStyle(top3Workbook, IndexedColors.ROSE.getIndex());
            CellStyle top10HeaderStyle = createHeaderStyle(top10Workbook, IndexedColors.PALE_BLUE.getIndex());

            String[] columns = {"Ранг", "Муниципалитет", "Кол-во проблем", "Ключевые темы", "Отчёт AI"};
            createHeaderRow(top3Sheet, columns, top3HeaderStyle);
            createHeaderRow(top10Sheet, columns, top10HeaderStyle);

            int rank = 1;
            for (int i = 0; i < results.length; i++) {
                FinalReportRow reportRow = results[i];
                fillDataRow(top10Sheet.createRow(i + 1), rank, reportRow);
                if (i < 3) fillDataRow(top3Sheet.createRow(i + 1), rank, reportRow);
                rank++;
            }

            autoSizeColumns(top3Sheet, columns.length);
            autoSizeColumns(top10Sheet, columns.length);

            top3Workbook.write(bosTop3);
            top3Workbook.dispose();
            top3ExcelBytes = bosTop3.toByteArray();

            top10Workbook.write(bosTop10);
            top10Workbook.dispose();
            top10ExcelBytes = bosTop10.toByteArray();
        }

        byte[] wordBytes = createWordReport(grandSummary);

        log.info("Файлы сгенерированы! Упаковываем в ZIP...");
        byte[] zipBytes = createZipArchive(top3ExcelBytes, top10ExcelBytes, wordBytes);
        return new ReportResult(zipBytes, grandSummary);
    }

    private byte[] createWordReport(String grandSummary) throws IOException {
        try (XWPFDocument document = new XWPFDocument();
             ByteArrayOutputStream bos = new ByteArrayOutputStream()) {

            XWPFParagraph title = document.createParagraph();
            title.setAlignment(ParagraphAlignment.CENTER);
            XWPFRun titleRun = title.createRun();
            titleRun.setText("Глобальная аналитическая выжимка");
            titleRun.setBold(true);
            titleRun.setFontSize(16);

            XWPFParagraph body = document.createParagraph();
            XWPFRun bodyRun = body.createRun();

            String[] lines = grandSummary.split("\n");
            for (int i = 0; i < lines.length; i++) {
                bodyRun.setText(lines[i]);
                if (i < lines.length - 1) bodyRun.addBreak();
            }

            document.write(bos);
            return bos.toByteArray();
        }
    }

    private byte[] createZipArchive(byte[] top3ExcelBytes, byte[] top10ExcelBytes, byte[] wordBytes) throws IOException {
        try (ByteArrayOutputStream bos = new ByteArrayOutputStream();
             ZipOutputStream zos = new ZipOutputStream(bos)) {

            ZipEntry top3Entry = new ZipEntry("top3_report.xlsx");
            zos.putNextEntry(top3Entry);
            zos.write(top3ExcelBytes);
            zos.closeEntry();

            ZipEntry top10Entry = new ZipEntry("top10_report.xlsx");
            zos.putNextEntry(top10Entry);
            zos.write(top10ExcelBytes);
            zos.closeEntry();

            ZipEntry wordEntry = new ZipEntry("summary.docx");
            zos.putNextEntry(wordEntry);
            zos.write(wordBytes);
            zos.closeEntry();

            return bos.toByteArray();
        }
    }

    private CellStyle createHeaderStyle(Workbook workbook, short colorIndex) {
        CellStyle style = workbook.createCellStyle();
        style.setFillForegroundColor(colorIndex);
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        Font font = workbook.createFont();
        font.setBold(true);
        style.setFont(font);
        return style;
    }

    private void createHeaderRow(Sheet sheet, String[] columns, CellStyle style) {
        Row headerRow = sheet.createRow(0);
        for (int i = 0; i < columns.length; i++) {
            Cell cell = headerRow.createCell(i);
            cell.setCellValue(columns[i]);
            cell.setCellStyle(style);
        }
    }

    private void fillDataRow(Row dataRow, int rank, FinalReportRow reportRow) {
        dataRow.createCell(0).setCellValue(rank);
        dataRow.createCell(1).setCellValue(reportRow.district());
        dataRow.createCell(2).setCellValue(reportRow.problemCount());
        dataRow.createCell(3).setCellValue(reportRow.topIssues());
        dataRow.createCell(4).setCellValue(reportRow.summary());
    }

    private void autoSizeColumns(SXSSFSheet sheet, int columnCount) {
        sheet.trackAllColumnsForAutoSizing();
        for (int i = 0; i < columnCount; i++) {
            sheet.autoSizeColumn(i);
        }
    }

    private String getCellAsString(Row row, int cellIndex) {
        Cell cell = row.getCell(cellIndex, Row.MissingCellPolicy.RETURN_BLANK_AS_NULL);
        if (cell == null) return "";

        return switch (cell.getCellType()) {
            case STRING -> cell.getStringCellValue();
            case NUMERIC -> String.valueOf((long) cell.getNumericCellValue());
            case BOOLEAN -> String.valueOf(cell.getBooleanCellValue());
            default -> "";
        };
    }
}