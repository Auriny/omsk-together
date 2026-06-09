package ru.auriny.core.dto;

public record ReportResult(
        byte[] archiveBytes,
        String grandSummary
) {}