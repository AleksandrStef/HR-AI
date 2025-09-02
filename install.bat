@echo off
echo 🤖 HR AI - Установка системы анализа ПИР
echo ==========================================

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден. Пожалуйста, установите Python 3.8+ с https://python.org
    pause
    exit /b 1
)

echo ✅ Python найден

REM Создание виртуального окружения
echo 🔧 Создание виртуального окружения...
python -m venv env
if errorlevel 1 (
    echo ❌ Ошибка создания виртуального окружения
    pause
    exit /b 1
)

REM Активация окружения
echo 🔧 Активация виртуального окружения...
call env\Scripts\activate.bat

REM Установка зависимостей
echo 📦 Установка зависимостей...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Ошибка установки зависимостей
    pause
    exit /b 1
)

REM Создание .env файла
echo 🔧 Создание файла конфигурации...
if not exist .env (
    copy .env.example .env
    echo ✅ Создан файл .env
) else (
    echo ⚠️ Файл .env уже существует
)

REM Создание папки для документов
if not exist docs (
    mkdir docs
    echo ✅ Создана папка docs для документов ПИР
)

REM Запуск тестов
echo 🧪 Запуск тестирования системы...
python test_runner.py

echo.
echo ✅ Установка завершена!
echo.
echo 📋 Следующие шаги:
echo 1. Поместите документы ПИР в папку docs/
echo 2. (Опционально) Добавьте OpenAI API ключ в .env файл
echo 3. (Опционально) Настройте уведомления в .env файле
echo 4. Запустите веб-интерфейс: python main.py web
echo.
echo 📚 Команды:
echo   python main.py web       - Веб-интерфейс
echo   python main.py analyze   - Ручной анализ
echo   python main.py schedule  - Планировщик
echo.
pause