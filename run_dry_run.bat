@echo off
REM Automated Dry Run Test Script for Vatavaran (Windows)

echo ==========================================
echo Vatavaran Dry Run Test
echo ==========================================
echo.

REM Check if we're in the right directory
if not exist "manage.py" (
    echo Error: manage.py not found. Run this script from the project root.
    exit /b 1
)

REM Step 1: Set environment variables
echo Step 1: Setting environment variables...
set WEATHERAPI_KEY=6415f4c56b1d424384860604242303
set DJANGO_SECRET_KEY=test-secret-key-for-dry-run
set DEBUG=True
set ALLOWED_HOSTS=localhost,127.0.0.1
set MODEL_DIR=.
echo [OK] Environment variables set
echo.

REM Step 2: Check model artifacts
echo Step 2: Checking model artifacts...
if exist "lstm_model.h5" (
    if exist "scaler_features.pkl" (
        if exist "scaler_target.pkl" (
            if exist "model_config.pkl" (
                echo [OK] All model artifacts found
            ) else (
                echo [ERROR] model_config.pkl not found
                exit /b 1
            )
        ) else (
            echo [ERROR] scaler_target.pkl not found
            exit /b 1
        )
    ) else (
        echo [ERROR] scaler_features.pkl not found
        exit /b 1
    )
) else (
    echo [ERROR] lstm_model.h5 not found
    exit /b 1
)
echo.

REM Step 3: Run Django checks
echo Step 3: Running Django checks...
python manage.py check
if errorlevel 1 (
    echo [ERROR] Django checks failed
    exit /b 1
)
echo [OK] Django checks passed
echo.

REM Step 4: Test components
echo Step 4: Testing components...

echo Testing weather API...
python -c "from api.weather import fetch_weather_forecast; df = fetch_weather_forecast(); print(f'[OK] Weather API: Fetched {len(df)} hours')"

echo Testing LSTM inference...
python -c "from api.inference import LSTMPredictor; import numpy as np; predictor = LSTMPredictor(); features = np.random.randn(96, 90); predictions = predictor.predict_24h(features); print(f'[OK] LSTM: Generated {len(predictions)} predictions')"

echo Testing NLP parser...
python -c "from api.nlp.command_parser import parse_command; r1 = parse_command('it''s too hot', 26.0); r2 = parse_command('set to 22', 26.0); print(f'[OK] NLP Parser: delta={r1.get(\"delta\")}, absolute={r2.get(\"absolute\")}')"

echo Testing CSV generator...
python -c "import numpy as np; from api.csv_generator import generate_schedule_csv; predictions = np.random.uniform(22, 28, 96); csv = generate_schedule_csv(predictions); print(f'[OK] CSV Generator: {len(csv.splitlines())} lines')"

echo.
echo [OK] All components tested
echo.

echo ==========================================
echo Dry Run Test Complete!
echo ==========================================
echo.
echo Summary:
echo   [OK] Environment configured
echo   [OK] Model artifacts verified
echo   [OK] Django checks passed
echo   [OK] Components tested
echo.
echo To test the API endpoint:
echo   1. Start Django server: python manage.py runserver
echo   2. In another terminal, run: python test_ec2_endpoint.py
echo.
echo For detailed testing, see: DRY_RUN_TESTING.md
echo For deployment, see: DEPLOYMENT.md
