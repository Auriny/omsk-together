package ru.auriny.core.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import ru.auriny.core.service.ExcelService;

import java.io.IOException;
import java.time.Instant;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class IncidentController {
    private final ExcelService excelService;

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> analyzeIncidents(@RequestParam("file") MultipartFile file) throws IOException {
        byte[] excelReport = excelService.processAndGenerateReport(file);

        ByteArrayResource resource = new ByteArrayResource(excelReport);
        var time = LocalDate.now().format(DateTimeFormatter.ofPattern("dd-MM-yyyy"));

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"));
        headers.setContentDispositionFormData("attachment", String.format("summary_report_%s.xlsx", time));

        return ResponseEntity.ok().headers(headers).body(resource);
    }
}