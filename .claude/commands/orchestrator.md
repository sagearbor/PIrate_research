# 🎯 Fully Autonomous Cross-Platform Orchestrator

You are the Orchestrator Agent. You will autonomously analyze the project, create worktrees, launch agents, and coordinate based on the actual project state. Works on macOS, Linux, and WSL.

## Current Request
$ARGUMENTS

## Autonomous Execution

```bash
echo "🎯 Starting Autonomous Multi-Agent Orchestration..."

# Step 1: Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
elif [[ "$OSTYPE" == "linux"* ]] && [[ -n "$WSL_DISTRO_NAME" ]]; then
    PLATFORM="WSL"
elif [[ "$OSTYPE" == "linux"* ]]; then
    PLATFORM="Linux"
else
    PLATFORM="Unknown"
fi
echo "🖥️ Detected platform: $PLATFORM"

# Step 2: Analyze project state first
echo "📊 Analyzing project state and development checklist..."
if [ -f "development_checklist.yaml" ]; then
    echo "✅ Found development checklist"
    cat development_checklist.yaml
else
    echo "⚠️ No development checklist found - will create one"
fi

# Step 3: Get current branch dynamically
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Current branch: $CURRENT_BRANCH"

# Step 4: Clean up any existing worktrees (for re-runs)
echo "🧹 Cleaning up any existing worktrees..."
git worktree remove ../research-notifier-dev 2>/dev/null || true
git worktree remove ../research-notifier-qa 2>/dev/null || true
git worktree remove ../research-notifier-devops 2>/dev/null || true
git worktree remove ../research-notifier-infra 2>/dev/null || true

# Step 5: Create fresh worktrees from CURRENT branch
echo "📁 Creating git worktrees from branch: $CURRENT_BRANCH..."
git worktree add ../research-notifier-dev $CURRENT_BRANCH
git worktree add ../research-notifier-qa $CURRENT_BRANCH  
git worktree add ../research-notifier-devops $CURRENT_BRANCH
git worktree add ../research-notifier-infra $CURRENT_BRANCH

# Step 6: Copy configurations to ALL worktrees
echo "⚙️ Copying configurations to all worktrees..."
for worktree in dev qa devops infra; do
    echo "  Copying to research-notifier-${worktree}..."
    
    # Copy Claude configurations
    cp -r .claude ../research-notifier-${worktree}/ 2>/dev/null || true
    
    # Copy project files
    cp development_checklist.yaml ../research-notifier-${worktree}/ 2>/dev/null || true
    cp README.md ../research-notifier-${worktree}/ 2>/dev/null || true
    cp requirements.txt ../research-notifier-${worktree}/ 2>/dev/null || true
    
    # Copy project directories
    cp -r src ../research-notifier-${worktree}/ 2>/dev/null || true
    cp -r config ../research-notifier-${worktree}/ 2>/dev/null || true
    cp -r tests ../research-notifier-${worktree}/ 2>/dev/null || true
done

echo "✅ All configurations copied to all worktrees"

# Step 7: Launch Claude Code instances with platform-specific commands
echo "🚀 Launching autonomous agents for $PLATFORM..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS Terminal
    osascript -e 'tell application "Terminal" 
        do script "cd ../research-notifier-dev && echo \"🔨 Developer Agent - Ready\" && claude"
    end tell' &
    
    osascript -e 'tell application "Terminal"
        do script "cd ../research-notifier-qa && echo \"🧪 QA Agent - Ready\" && claude" 
    end tell' &
    
    osascript -e 'tell application "Terminal"
        do script "cd ../research-notifier-devops && echo \"🚀 DevOps Agent - Ready\" && claude"
    end tell' &
    
    osascript -e 'tell application "Terminal"
        do script "cd ../research-notifier-infra && echo \"🏗️ Infrastructure Agent - Ready\" && claude"
    end tell' &

else
    # Linux/WSL - Use standard Linux terminal commands
    if command -v gnome-terminal &> /dev/null; then
        # GNOME Terminal (most common)
        gnome-terminal --tab --title="Developer" -- bash -c "cd ../research-notifier-dev && echo '🔨 Developer Agent - Ready' && claude" &
        gnome-terminal --tab --title="QA" -- bash -c "cd ../research-notifier-qa && echo '🧪 QA Agent - Ready' && claude" &
        gnome-terminal --tab --title="DevOps" -- bash -c "cd ../research-notifier-devops && echo '🚀 DevOps Agent - Ready' && claude" &
        gnome-terminal --tab --title="Infrastructure" -- bash -c "cd ../research-notifier-infra && echo '🏗️ Infrastructure Agent - Ready' && claude" &
    
    elif command -v konsole &> /dev/null; then
        # KDE Konsole
        konsole --new-tab -e bash -c "cd ../research-notifier-dev && claude" &
        konsole --new-tab -e bash -c "cd ../research-notifier-qa && claude" &
        konsole --new-tab -e bash -c "cd ../research-notifier-devops && claude" &
        konsole --new-tab -e bash -c "cd ../research-notifier-infra && claude" &
    
    elif command -v xterm &> /dev/null; then
        # Basic X11 terminal
        xterm -T "Developer" -e "cd ../research-notifier-dev && claude" &
        xterm -T "QA" -e "cd ../research-notifier-qa && claude" &
        xterm -T "DevOps" -e "cd ../research-notifier-devops && claude" &
        xterm -T "Infrastructure" -e "cd ../research-notifier-infra && claude" &
    
    else
        # Fallback: Manual instructions
        echo "📋 Please manually open 4 terminals and run:"
        echo "Terminal 1: cd ../research-notifier-dev && claude"
        echo "Terminal 2: cd ../research-notifier-qa && claude"  
        echo "Terminal 3: cd ../research-notifier-devops && claude"
        echo "Terminal 4: cd ../research-notifier-infra && claude"
    fi
fi

sleep 3
echo "✅ All agent terminals launched (or instructions provided)"

# Step 8: Instructions for each platform
echo "🎭 Next steps for $PLATFORM:"
if [[ "$PLATFORM" == "WSL" ]]; then
    echo "   • In each Windows Terminal tab, press Shift+Tab for auto-accept mode"
    echo "   • Run the appropriate agent command in each terminal"
else
    echo "   • In each terminal, press Shift+Tab for auto-accept mode"  
    echo "   • Run the appropriate agent command in each terminal"
fi

echo "🔄 Multi-agent autonomous orchestration setup complete!"