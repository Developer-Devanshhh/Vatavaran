# Design Document: Vatavaran Climate Control System

## Overview

Vatavaran is a distributed smart climate control system that predicts and automates AC temperature settings using LSTM-based machine learning. The system operates across two computing environments: a Raspberry Pi 4 for edge sensing and control, and an AWS EC2 instance for ML inference and weather integration. The RPi collects sensor data and voice commands, sends them to EC2 for processing, receives a 24-hour temperature schedule (96 15-minute slots), and executes IR commands to control the AC unit. The system supports two trigger modes: scheduled execution every 15 minutes, and voice command overrides for immediate adjustments.

## Architecture

```mermaid
graph TB
    subgraph "Raspberry Pi 4 - Edge Device"
        A[Temperature Sensor] --> B[Sensor Reader]
        C[Microphone] --> D[STT Module Vosk/Whisper]
        B --> E[Payload Builder]
        D --> E
        E --> F[HTTP Client]
        F --> |POST /api/predict/| G[Network]
        G --> |schedule.csv| H[CSV Parser]
        H --> I[IR Blaster Controller]
        I --> J[IR LED]
        J -.->|IR Signal| K[AC Unit]
        L[Cron Scheduler] -.->|Every 15 min| E
        M[Voice Button] -.->|Trigger| D
    end
    
    subgraph "AWS EC2 - Django Server"
        G --> N[Django API Endpoint]
        N --> O[Weather API Client]
        N --> P[Feature Engineering]
        N --> Q[LSTM Inference Engine]
        N --> R[NLP Command Parser]
        N --> S[CSV Generator]
        O --> |Weather Data| P
        P --> |90 Features| Q
        Q --> |96 Predictions| S
        R --> |Override Delta| S
        S --> |schedule.csv| N
        T[Model Artifacts] --> Q
        U[WeatherAPI.com] --> O
    end
    
    style K fill:#f9f,stroke:#333,stroke-width:2px
    style T fill:#bbf,stroke:#333,stroke-width:2px
    style U fill:#bfb,stroke:#333,stroke-width:2px
```

## Main Workflow Sequence Diagrams

### Scheduled Mode (Every 15 Minutes)

```mermaid
sequenceDiagram
    participant Cron as Cron Job
    participant Sensor as Sensor Reader
    participant Client as Pipeline Client
    participant EC2 as Django API
    participant Weather as WeatherAPI
    participant LSTM as LSTM Engine
    participant CSV as CSV Generator
    participant IR as IR Blaster
    
    Cron->>Client: Trigger scheduled execution
    Client->>Sensor: Read current temperature
    Sensor-->>Client: {timestamp, temp_c, device_id}
    Client->>EC2: POST /api/predict/ (mode: scheduled)
    EC2->>Weather: Fetch 24h forecast
    Weather-->>EC2: Hourly weather data
    EC2->>EC2: Build 90-feature matrix
    EC2->>LSTM: Predict 96 slots
    LSTM-->>EC2: 96 temperature predictions
    EC2->>CSV: Generate schedule.csv
    CSV-->>EC2: CSV with 96 rows
    EC2-->>Client: Return schedule.csv
    Client->>Client: Save to /home/pi/vatavaran/schedule.csv
    IR->>IR: Read current slot from CSV
    IR->>IR: Map temp to IR code
    IR->>IR: Fire IR signal to AC
```

### Voice Override Mode

```mermaid
sequenceDiagram
    participant User as User
    participant Button as Voice Button
    participant STT as STT Module
    participant Client as Pipeline Client
    participant EC2 as Django API
    participant NLP as NLP Parser
    participant CSV as CSV Generator
    participant IR as IR Blaster
    
    User->>Button: Press button / say wake word
    Button->>STT: Trigger recording (5 sec)
    User->>STT: "It's too hot"
    STT->>STT: Vosk/Whisper transcription
    STT-->>Client: "it's too hot"
    Client->>Client: Read sensor data
    Client->>EC2: POST /api/predict/ (mode: voice_override, command_text)
    EC2->>EC2: Fetch weather & build features
    EC2->>EC2: Run LSTM predictions
    EC2->>NLP: Parse command with current temp
    NLP-->>EC2: {delta: -2} or {absolute: 22}
    EC2->>CSV: Apply override to next 4 slots
    CSV-->>EC2: Updated schedule.csv
    EC2-->>Client: Return schedule.csv
    Client->>Client: Save schedule.csv
    IR->>IR: Detect schedule change
    IR->>IR: Apply new temperature immediately
    IR->>IR: Fire IR signal to AC
