package ru.auriny.core.service;

import com.github.pjfanning.xlsx.StreamingReader;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.streaming.SXSSFSheet;
import org.apache.poi.xssf.streaming.SXSSFWorkbook;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import ru.auriny.core.dto.AnalyzeTaskBatch;
import ru.auriny.core.dto.FinalReportRow;
import ru.auriny.core.dto.IncidentRow;
import ru.auriny.core.util.RedisKeys;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ExcelService {
    private final AiQueueService aiQueueService;
    private static final int BATCH_SIZE = 50;

    public byte[] processAndGenerateReport(MultipartFile file) throws IOException {
        log.info("Началась обработка файла: {}", file.getOriginalFilename());
        // чтение и отправка батчей
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

                String topicGroup = getCellAsString(row, 19); // T: Группа тем
                String district = getCellAsString(row, 22); // W: Муниципалитет
                String text = getCellAsString(row, 34); // AI: Текст инцидента

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

        // ждем ответ от llm сервиса
        log.info("Ждем генерации саммари от Qwen..."); // V таймаут
        FinalReportRow[] results = aiQueueService.waitForResult(RedisKeys.QUEUE_RESULTS, FinalReportRow[].class, 1200);

        if (results == null || results.length == 0) {
            throw new RuntimeException("Не удалось получить результат от AI-модуля (таймаут или ошибка)");
        }

        // как дождались - генерим отчет
        try (SXSSFWorkbook writeWorkbook = new SXSSFWorkbook(100);
             ByteArrayOutputStream bos = new ByteArrayOutputStream()) {

            SXSSFSheet top3Sheet = writeWorkbook.createSheet("Топ-3: критичные");
            SXSSFSheet top10Sheet = writeWorkbook.createSheet("Топ-10: общий список");

            CellStyle headerStyle = createHeaderStyle(writeWorkbook);
            String[] columns = {"Ранг", "Муниципалитет", "Кол-во проблем", "Ключевые темы", "Отчёт AI"};

            createHeaderRow(top3Sheet, columns, headerStyle);
            createHeaderRow(top10Sheet, columns, headerStyle);

            int rank = 1;
            for (int i = 0; i < results.length; i++) {
                FinalReportRow reportRow = results[i];
                fillDataRow(top10Sheet.createRow(i + 1), rank, reportRow);
                if (i < 3) fillDataRow(top3Sheet.createRow(i + 1), rank, reportRow);
                rank++;
            }

            autoSizeColumns(top3Sheet, columns.length);
            autoSizeColumns(top10Sheet, columns.length);

            writeWorkbook.write(bos);
            writeWorkbook.dispose(); // не уверен, что это нужно .c.

            log.info("Финальный отчет успешно сгенерирован и отправляется пользователю!!!");
            return bos.toByteArray();
        }
    }

    private CellStyle createHeaderStyle(Workbook workbook) {
        CellStyle style = workbook.createCellStyle();
        style.setFillForegroundColor(IndexedColors.PALE_BLUE.getIndex());
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