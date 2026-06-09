package ru.auriny.core.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import ru.auriny.core.dto.ReportResult;
import ru.auriny.core.service.ExcelService;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class IncidentController {
    private final ExcelService excelService;

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> analyzeIncidents(@RequestParam("file") MultipartFile file) throws IOException {
        ReportResult result = excelService.processAndGenerateReport(file);

        ByteArrayResource resource = new ByteArrayResource(result.archiveBytes());
        var time = LocalDate.now().format(DateTimeFormatter.ofPattern("dd-MM-yyyy"));

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("application/zip"));
        headers.setContentDispositionFormData("attachment", String.format("analytics_pack_%s.zip", time));

        String encodedSummary = URLEncoder.encode(result.grandSummary(), StandardCharsets.UTF_8);

        headers.add("Access-Control-Expose-Headers", "X-Summary");
        headers.add("X-Summary", encodedSummary);

        return ResponseEntity.ok().headers(headers).body(resource);
    }
}