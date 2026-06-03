package ru.auriny.core.dto;

public record FinalReportRow(
        String district,
        int problemCount,
        String topIssues,
        String summary
) {}