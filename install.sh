#!/bin/bash

echo "🤖 HR AI - Установка системы анализа ПИР"
echo "=========================================="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Пожалуйста, установите Python 3.8+"
    exit 1
fi

echo "✅ Python найден"

# Создание виртуального окружения
echo "🔧 Создание виртуального окружения..."
python3 -m venv env
if [ $? -ne 0 ]; then
    echo "❌ Ошибка создания виртуального окружения"
    exit 1
fi

# Активация окружения
echo "🔧 Активация виртуального окружения..."
source env/bin/activate

# Установка зависимостей
echo "📦 Установка зависимостей..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Ошибка установки зависимостей"
    exit 1
fi

# Создание .env файла
echo "🔧 Создание файла конфигурации..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Создан файл .env"
else
    echo "⚠️ Файл .env уже существует"
fi

# Создание папки для документов
if [ ! -d docs ]; then
    mkdir docs
    echo "✅ Создана папка docs для документов ПИР"
fi

# Запуск тестов
echo "🧪 Запуск тестирования системы..."
python test_runner.py

echo ""
echo "✅ Установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Поместите документы ПИР в папку docs/"
echo "2. (Опционально) Добавьте OpenAI API ключ в .env файл"
echo "3. (Опционально) Настройте уведомления в .env файле"
echo "4. Запустите веб-интерфейс: python main.py web"
echo ""
echo "📚 Команды:"
echo "  python main.py web       - Веб-интерфейс"
echo "  python main.py analyze   - Ручной анализ"
echo "  python main.py schedule  - Планировщик"
echo ""