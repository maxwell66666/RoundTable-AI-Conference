#!/bin/bash
# 脚本用于在Linux系统上设置自动备份的cron任务

# 获取当前目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 检查是否有sudo权限
if [[ $EUID -ne 0 ]]; then
   echo "此脚本需要sudo权限运行。请使用sudo执行此脚本。"
   exit 1
fi

echo "设置RoundTable自动备份计划..."

# 创建备份脚本
BACKUP_SCRIPT="$SCRIPT_DIR/run_backup.sh"
cat > "$BACKUP_SCRIPT" << 'EOL'
#!/bin/bash
# 自动备份脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 激活Python虚拟环境（如果有）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 运行备份
python backup.py create

# 记录日志
echo "备份已于 $(date) 完成" >> backup_cron.log
EOL

# 设置执行权限
chmod +x "$BACKUP_SCRIPT"

# 询问备份频率
echo "请选择备份频率:"
echo "1) 每天"
echo "2) 每周"
echo "3) 每月"
read -p "请输入选项(1-3): " FREQUENCY

# 询问备份时间
read -p "请输入备份时间 (24小时制，例如: 02:00): " BACKUP_TIME

# 解析时间
HOUR=$(echo $BACKUP_TIME | cut -d':' -f1)
MINUTE=$(echo $BACKUP_TIME | cut -d':' -f2)

# 构建cron表达式
case $FREQUENCY in
    1) # 每天
        CRON_EXPR="$MINUTE $HOUR * * *"
        FREQ_DESC="每天 $BACKUP_TIME"
        ;;
    2) # 每周（星期日）
        CRON_EXPR="$MINUTE $HOUR * * 0"
        FREQ_DESC="每周日 $BACKUP_TIME"
        ;;
    3) # 每月（1号）
        CRON_EXPR="$MINUTE $HOUR 1 * *"
        FREQ_DESC="每月1号 $BACKUP_TIME"
        ;;
    *)
        echo "无效选项，使用默认设置：每天 02:00"
        CRON_EXPR="0 2 * * *"
        FREQ_DESC="每天 02:00"
        ;;
esac

# 创建临时cron文件
TEMP_CRON=$(mktemp)
crontab -l > "$TEMP_CRON" 2>/dev/null || echo "" > "$TEMP_CRON"

# 检查是否已存在RoundTable备份的cron任务
if grep -q "RoundTable备份" "$TEMP_CRON"; then
    # 替换已有的任务
    sed -i "/# RoundTable备份/,+1d" "$TEMP_CRON"
fi

# 添加新任务
echo "# RoundTable备份" >> "$TEMP_CRON"
echo "$CRON_EXPR $BACKUP_SCRIPT" >> "$TEMP_CRON"

# 安装新的cron任务
crontab "$TEMP_CRON"
rm "$TEMP_CRON"

echo "Cron任务已设置，将在$FREQ_DESC执行备份"
echo "备份脚本路径: $BACKUP_SCRIPT"
echo "备份日志: $SCRIPT_DIR/backup_cron.log"
echo ""
echo "要查看当前的cron任务，请运行 'crontab -l'"
echo "要手动修改任务，请运行 'crontab -e'" 