package controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import ru.auriny.core.CoreApplication;
import ru.auriny.core.controller.IncidentController;
import ru.auriny.core.dto.ReportResult;
import ru.auriny.core.service.ExcelService;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

import static org.hamcrest.Matchers.containsString;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(controllers = IncidentController.class)
@ContextConfiguration(classes = CoreApplication.class)
public class IncidentControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private ExcelService excelService;

    @Test
    void analyzeIncidentsReturnsZipAndSummaryHeader() throws Exception {
        byte[] archiveBytes = new byte[] { 1, 2, 3 };
        String summary = "Summary line 1\nSummary line 2";

        ReportResult result = new ReportResult(archiveBytes, summary);
        when(excelService.processAndGenerateReport(any())).thenReturn(result);

        MockMultipartFile file = new MockMultipartFile(
                "file",
                "data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                new byte[] { 0, 1, 2 });

        String expectedTime = LocalDate.now().format(DateTimeFormatter.ofPattern("dd-MM-yyyy"));
        String expectedFileName = "analytics_pack_" + expectedTime + ".zip";
        String encodedSummary = URLEncoder.encode(summary, StandardCharsets.UTF_8);

        mockMvc.perform(MockMvcRequestBuilders.multipart("/api/upload").file(file))
                .andExpect(status().isOk())
                .andExpect(content().contentType("application/zip"))
                .andExpect(header().string("X-Summary", encodedSummary))
                .andExpect(header().string("Content-Disposition", containsString(expectedFileName)));
    }

    @Test
    void analyzeIncidentsReturnsErrorWhenInvalidFile() throws Exception {
        doThrow(new IllegalArgumentException("Только файлы .xlsx допускаются"))
                .when(excelService).processAndGenerateReport(any());

        MockMultipartFile file = new MockMultipartFile(
                "file",
                "data.xls",
                "application/vnd.ms-excel",
                new byte[] { 0, 1, 2 });

        jakarta.servlet.ServletException exception = assertThrows(
                jakarta.servlet.ServletException.class,
                () -> mockMvc.perform(MockMvcRequestBuilders.multipart("/api/upload").file(file)).andReturn());

        assertInstanceOf(IllegalArgumentException.class, exception.getCause());
    }
}
