#!/bin/bash
# Final validation before GitHub deployment

echo "🔍 Final Validation - AI Voice Robot Raspberry Pi 5"
echo "=================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SUCCESS=0
WARNINGS=0
ERRORS=0

check_file() {
    local file=$1
    local desc=$2
    
    if [ -f "$file" ]; then
        echo -e "✅ $desc: ${GREEN}OK${NC}"
        ((SUCCESS++))
    else
        echo -e "❌ $desc: ${RED}MISSING${NC}"
        ((ERRORS++))
    fi
}

check_executable() {
    local file=$1
    local desc=$2
    
    if [ -f "$file" ]; then
        if [ -x "$file" ]; then
            echo -e "✅ $desc: ${GREEN}OK (executable)${NC}"
            ((SUCCESS++))
        else
            echo -e "⚠️  $desc: ${YELLOW}OK but not executable${NC}"
            ((WARNINGS++))
        fi
    else
        echo -e "❌ $desc: ${RED}MISSING${NC}"
        ((ERRORS++))
    fi
}

# Check core files
echo "📋 Checking core files:"
check_file "main_raspy.py" "Main application"
check_file "text_to_voice_raspy.py" "TTS module"
check_file "serial_monitor.py" "Serial monitor"
check_file "requirements_raspy.txt" "Requirements"
check_file "ESP32_Robot_RaspyPi5.ino" "ESP32 Arduino code"
echo ""

# Check scripts
echo "📋 Checking scripts:"
check_executable "quick_start.sh" "Quick start script"
check_executable "setup_raspy.sh" "Setup script"
check_executable "run_raspy.sh" "Run script"
check_executable "setup_gpio_uart.sh" "GPIO UART setup"
check_executable "test_uart.sh" "UART test"
check_executable "monitor_esp32.sh" "ESP32 monitor"
echo ""

# Check documentation
echo "📋 Checking documentation:"
check_file "README.md" "Original README"
check_file "README_GITHUB.md" "GitHub README"
check_file "DEPLOYMENT_CHECKLIST.md" "Deployment checklist"
echo ""

# Check script syntax
echo "📋 Checking script syntax:"
for script in *.sh; do
    if [ -f "$script" ]; then
        bash -n "$script" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "✅ $script: ${GREEN}Syntax OK${NC}"
            ((SUCCESS++))
        else
            echo -e "❌ $script: ${RED}Syntax ERROR${NC}"
            ((ERRORS++))
        fi
    fi
done
echo ""

# Check Python syntax
echo "📋 Checking Python syntax:"
for pyfile in *.py; do
    if [ -f "$pyfile" ]; then
        python3 -m py_compile "$pyfile" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "✅ $pyfile: ${GREEN}Syntax OK${NC}"
            ((SUCCESS++))
        else
            echo -e "❌ $pyfile: ${RED}Syntax ERROR${NC}"
            ((ERRORS++))
        fi
    fi
done
echo ""

# Check file sizes (detect empty files)
echo "📋 Checking file sizes:"
for file in *.py *.sh *.md *.txt *.ino; do
    if [ -f "$file" ]; then
        size=$(stat -c%s "$file" 2>/dev/null || echo "0")
        if [ "$size" -gt 100 ]; then
            echo -e "✅ $file: ${GREEN}${size} bytes${NC}"
            ((SUCCESS++))
        else
            echo -e "⚠️  $file: ${YELLOW}${size} bytes (very small)${NC}"
            ((WARNINGS++))
        fi
    fi
done
echo ""

# Summary
echo "📊 VALIDATION SUMMARY:"
echo "====================="
echo -e "✅ Success: ${GREEN}$SUCCESS${NC}"
echo -e "⚠️  Warnings: ${YELLOW}$WARNINGS${NC}" 
echo -e "❌ Errors: ${RED}$ERRORS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}🎉 READY FOR GITHUB DEPLOYMENT!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Create GitHub repository"
    echo "2. Upload all files"
    echo "3. Test clone & setup on Pi 5"
    echo ""
    
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Note: Fix warnings for better experience${NC}"
    fi
    
    exit 0
else
    echo -e "${RED}❌ NOT READY - Fix errors first!${NC}"
    exit 1
fi