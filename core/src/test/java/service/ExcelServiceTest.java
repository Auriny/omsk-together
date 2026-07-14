package service;

import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;
import ru.auriny.core.dto.FinalReportRow;
import ru.auriny.core.dto.IncidentRow;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.ArrayList;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

public class ExcelServiceTest {

    private byte[] createXlsxWithRows(IncidentRow... rows) throws IOException {
        try (XSSFWorkbook workbook = new XSSFWorkbook();
                ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            Sheet sheet = workbook.createSheet();

            Row header = sheet.createRow(0);
            for (int i = 0; i <= 34; i++) {
                header.createCell(i).setCellValue("col" + i);
            }

            int rowIndex = 1;
            for (IncidentRow incident : rows) {
                Row dataRow = sheet.createRow(rowIndex++);
                if (incident.topic() != null) {
                    dataRow.createCell(19).setCellValue(incident.topic());
                }
                if (incident.district() != null) {
                    dataRow.createCell(22).setCellValue(incident.district());
                }
                if (incident.text() != null) {
                    dataRow.createCell(34).setCellValue(incident.text());
                }
            }

            workbook.write(out);
            return out.toByteArray();
        }
    }

    @Test
    void processAndGenerateReportRejectsNonXlsx() {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        MultipartFile file = new MockMultipartFile(
                "file",
                "test.xls",
                "application/vnd.ms-excel",
                new byte[] {});

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> excelService.processAndGenerateReport(file));

        assertTrue(exception.getMessage().contains(".xlsx"));
    }

    @Test
    void processAndGenerateReportWithEmptyXlsx() throws IOException {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        byte[] emptyXlsxBytes = null;

        MultipartFile file = new MockMultipartFile(
                "file",
                "empty.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                emptyXlsxBytes);

        when(aiQueueService.waitForResult(
                ru.auriny.core.util.RedisKeys.QUEUE_RESULTS,
                ru.auriny.core.dto.FinalReportRow[].class,
                8000)).thenReturn(null);

        when(aiQueueService.waitForResult(
                ru.auriny.core.util.RedisKeys.QUEUE_SUMMARY,
                String.class,
                8000)).thenReturn(null);

        assertThrows(RuntimeException.class, () -> excelService.processAndGenerateReport(file));
    }

    @Test
    void processAndGenerateReportRejectsNullFilename() {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        MultipartFile file = Mockito.mock(MultipartFile.class);
        when(file.getOriginalFilename()).thenReturn(null);

        assertThrows(IllegalArgumentException.class,
                () -> excelService.processAndGenerateReport(file));
    }

    @Test
    void processAndGenerateReportRejectsEmptyFilename() {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        MultipartFile file = new MockMultipartFile(
                "file",
                "",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                new byte[] {});

        assertThrows(IllegalArgumentException.class,
                () -> excelService.processAndGenerateReport(file));
    }

    @Test
    void processAndGenerateReportAcceptsXlsxVariants() {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_RESULTS,
                ru.auriny.core.dto.FinalReportRow[].class, 8000))
                .thenReturn(null);
        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_SUMMARY, String.class, 8000))
                .thenReturn(null);

        String[] names = { "file.xlsx", "FILE.XLSX", "file.Xlsx", "data_report.xlsx" };

        for (String name : names) {
            byte[] emptyXlsx = new byte[] {};
            MultipartFile file = new MockMultipartFile(
                    "file",
                    name,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    emptyXlsx);

            assertThrows(RuntimeException.class,
                    () -> excelService.processAndGenerateReport(file));
        }
    }

    @Test
    void processAndGenerateReportSkipsRowsWithoutText() throws IOException {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        byte[] xlsx = createXlsxWithRows(
                new IncidentRow("D1", "TG1", ""), // пустой
                new IncidentRow("D2", "TG2", null), // null
                new IncidentRow("D3", "TG3", "   "), // blank
                new IncidentRow("D4", "TG4", "Ok text") // +
        );

        MultipartFile file = new MockMultipartFile(
                "file", "data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                xlsx);

        FinalReportRow reportRow = new FinalReportRow(
                "D4", 1, "Issue", "Hard", "District summary");
        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_RESULTS, FinalReportRow[].class, 8000))
                .thenReturn(new FinalReportRow[] { reportRow });
        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_SUMMARY, String.class, 8000))
                .thenReturn("Summary");

        ru.auriny.core.dto.ReportResult result = excelService.processAndGenerateReport(file);

        assertNotNull(result);
        verify(aiQueueService, times(2))
                .pushTask(eq(ru.auriny.core.util.RedisKeys.QUEUE_TASKS),
                        any(ru.auriny.core.dto.AnalyzeTaskBatch.class));
    }

    @Test
    void processAndGenerateReportBatchesByBatchSize() throws IOException {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        int rows = 150;
        ArrayList<IncidentRow> rowData = new ArrayList<>();
        for (int i = 0; i < rows; i++) {
            rowData.add(new IncidentRow("TG", "D", "Text " + i));
        }

        byte[] xlsx = createXlsxWithRows(rowData.toArray(new IncidentRow[0]));

        MultipartFile file = new MockMultipartFile(
                "file", "big.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                xlsx);

        FinalReportRow reportRow = new FinalReportRow("D", 1, "T", "H", "S");
        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_RESULTS,
                FinalReportRow[].class, 8000))
                .thenReturn(new FinalReportRow[] { reportRow });
        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_SUMMARY, String.class, 8000))
                .thenReturn("Summary");

        ru.auriny.core.dto.ReportResult result = excelService.processAndGenerateReport(file);

        assertNotNull(result);
        verify(aiQueueService, times(4))
                .pushTask(eq(ru.auriny.core.util.RedisKeys.QUEUE_TASKS), any(ru.auriny.core.dto.AnalyzeTaskBatch.class));
    }

    @Test
    void processAndGenerateReportWithRealData() throws IOException {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        byte[] xlsxWithRows = createXlsxWithRows(
                new IncidentRow("District1", "TopicGroup1", "Sample text for analysis"));

        MultipartFile file = new MockMultipartFile(
                "file",
                "data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                xlsxWithRows);

        doNothing().when(aiQueueService).pushTask(anyString(), any(ru.auriny.core.dto.AnalyzeTaskBatch.class));

        FinalReportRow report1 = new FinalReportRow(
                "District1",
                10,
                "Issue1 (5), Issue2 (3)",
                "Hard1 (2)",
                "Summary for district 1");

        when(aiQueueService.waitForResult(
                ru.auriny.core.util.RedisKeys.QUEUE_RESULTS,
                FinalReportRow[].class,
                8000)).thenReturn(new FinalReportRow[] { report1 });

        when(aiQueueService.waitForResult(
                ru.auriny.core.util.RedisKeys.QUEUE_SUMMARY,
                String.class,
                8000)).thenReturn("Global summary");

        ru.auriny.core.dto.ReportResult result = excelService.processAndGenerateReport(file);

        assertNotNull(result);

        verify(aiQueueService, atLeastOnce()).pushTask(anyString(), any(ru.auriny.core.dto.AnalyzeTaskBatch.class));
    }

    @Test
    void processAndGenerateReportThrowsWhenResultsNull() throws IOException {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        byte[] xlsx = null;
        MultipartFile file = new MockMultipartFile(
                "file", "data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                xlsx);

        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_RESULTS,
                ru.auriny.core.dto.FinalReportRow[].class, 8000))
                .thenReturn(null);
        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_SUMMARY, String.class, 8000))
                .thenReturn("Summary");

        assertThrows(RuntimeException.class,
                () -> excelService.processAndGenerateReport(file));
    }

    @Test
    void processAndGenerateReportThrowsWhenResultsEmpty() throws IOException {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        byte[] xlsx = null;
        MultipartFile file = new MockMultipartFile(
                "file", "data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                xlsx);

        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_RESULTS,
                ru.auriny.core.dto.FinalReportRow[].class, 8000))
                .thenReturn(new FinalReportRow[] {});
        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_SUMMARY, String.class, 8000))
                .thenReturn("Summary");

        assertThrows(RuntimeException.class,
                () -> excelService.processAndGenerateReport(file));
    }

    @Test
    void processAndGenerateReportThrowsWhenSummaryNull() throws IOException {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        byte[] xlsx = null;
        MultipartFile file = new MockMultipartFile(
                "file", "data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                xlsx);

        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_RESULTS,
                ru.auriny.core.dto.FinalReportRow[].class, 8000))
                .thenReturn(new FinalReportRow[] { new FinalReportRow("D", 1, "T", "H", "S") });
        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_SUMMARY, String.class, 8000))
                .thenReturn(null);

        assertThrows(RuntimeException.class,
                () -> excelService.processAndGenerateReport(file));
    }

    @Test
    void processAndGenerateReportProducesValidZip() throws IOException {
        var aiQueueService = Mockito.mock(ru.auriny.core.service.AiQueueService.class);
        var excelService = new ru.auriny.core.service.ExcelService(aiQueueService);

        byte[] xlsx = createXlsxWithRows(
                new IncidentRow("TG", "D", "Text"));

        MultipartFile file = new MockMultipartFile(
                "file", "data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                xlsx);

        FinalReportRow row = new FinalReportRow("D", 1, "T", "H", "S");
        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_RESULTS, ru.auriny.core.dto.FinalReportRow[].class, 8000))
                .thenReturn(new FinalReportRow[] { row });
        when(aiQueueService.waitForResult(ru.auriny.core.util.RedisKeys.QUEUE_SUMMARY, String.class, 8000))
                .thenReturn("Summary line 1\nSummary line 2");

        ru.auriny.core.dto.ReportResult result = excelService.processAndGenerateReport(file);

        assertNotNull(result);
        byte[] zip = result.archiveBytes();
        assertTrue(zip.length > 0);

        try (var bais = new java.io.ByteArrayInputStream(zip);
                var zis = new java.util.zip.ZipInputStream(bais)) {

            boolean foundTop3 = false;
            boolean foundTop10 = false;
            boolean foundSummary = false;

            java.util.zip.ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                String name = entry.getName();
                if ("top3_report.xlsx".equals(name))
                    foundTop3 = true;
                if ("top10_report.xlsx".equals(name))
                    foundTop10 = true;
                if ("summary.docx".equals(name))
                    foundSummary = true;
            }

            assertTrue(foundTop3, "top3_report.xlsx должен быть в ZIP");
            assertTrue(foundTop10, "top10_report.xlsx должен быть в ZIP");
            assertTrue(foundSummary, "summary.docx должен быть в ZIP");
        }
    }
}
