package ru.auriny.core.dto;
import java.util.List;

public record AnalyzeTaskBatch(
        boolean isLastBatch,
        List<IncidentRow> items
) {}