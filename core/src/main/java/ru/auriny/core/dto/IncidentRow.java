package ru.auriny.core.dto;

public record IncidentRow(
        String district,
        String topic,
        String text
) {}