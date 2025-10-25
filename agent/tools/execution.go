package jarvisTools

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/tmc/langchaingo/tools"
)

type RunCodeTool struct{}

func (t RunCodeTool) Name() string {
	return "run_code"
}

func (t RunCodeTool) Description() string {
	return "Execute code in a specified language (supports Go, Python, JavaScript, etc.). Input should be JSON with 'code', 'language', and optional 'timeout' fields."
}

func (t RunCodeTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		Code     string `json:"code"`
		Language string `json:"language"`
		Timeout  int    `json:"timeout"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	if args.Timeout == 0 {
		args.Timeout = 30
	}

	return executeCode(args.Code, args.Language, args.Timeout)
}

type ExecuteTerminalTool struct{}

func (t ExecuteTerminalTool) Name() string {
	return "execute_terminal"
}

func (t ExecuteTerminalTool) Description() string {
	return "Execute terminal/shell commands. Input should be JSON with 'command', optional 'working_dir', and optional 'timeout' fields."
}

func (t ExecuteTerminalTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		Command    string `json:"command"`
		WorkingDir string `json:"working_dir"`
		Timeout    int    `json:"timeout"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	if args.Timeout == 0 {
		args.Timeout = 30
	}

	return executeTerminalCommand(args.Command, args.WorkingDir, args.Timeout)
}

type EvaluateExpressionTool struct{}

func (t EvaluateExpressionTool) Name() string {
	return "evaluate_expression"
}

func (t EvaluateExpressionTool) Description() string {
	return "Evaluate mathematical expressions or simple code snippets. Input should be JSON with 'expression' and optional 'language' fields."
}

func (t EvaluateExpressionTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		Expression string `json:"expression"`
		Language   string `json:"language"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	if args.Language == "" {
		args.Language = "python"
	}

	return evaluateExpression(args.Expression, args.Language)
}

func executeCode(code, language string, timeout int) (string, error) {
	tempDir, err := ioutil.TempDir("", "jarvis_exec_")
	if err != nil {
		return "", fmt.Errorf("failed to create temp directory: %v", err)
	}
	defer os.RemoveAll(tempDir)

	var cmd *exec.Cmd
	var fileName string

	switch strings.ToLower(language) {
	case "go":
		fileName = filepath.Join(tempDir, "main.go")
		err = ioutil.WriteFile(fileName, []byte(code), 0644)
		if err != nil {
			return "", fmt.Errorf("failed to write Go file: %v", err)
		}
		cmd = exec.Command("go", "run", fileName)

	case "python":
		fileName = filepath.Join(tempDir, "script.py")
		err = ioutil.WriteFile(fileName, []byte(code), 0644)
		if err != nil {
			return "", fmt.Errorf("failed to write Python file: %v", err)
		}
		cmd = exec.Command("python3", fileName)

	case "javascript", "js":
		fileName = filepath.Join(tempDir, "script.js")
		err = ioutil.WriteFile(fileName, []byte(code), 0644)
		if err != nil {
			return "", fmt.Errorf("failed to write JavaScript file: %v", err)
		}
		cmd = exec.Command("node", fileName)

	case "bash", "sh":
		fileName = filepath.Join(tempDir, "script.sh")
		err = ioutil.WriteFile(fileName, []byte(code), 0755)
		if err != nil {
			return "", fmt.Errorf("failed to write shell script: %v", err)
		}
		cmd = exec.Command("bash", fileName)

	default:
		return "", fmt.Errorf("unsupported language: %s", language)
	}

	cmd.Dir = tempDir

	done := make(chan error, 1)
	var output []byte

	go func() {
		output, err = cmd.CombinedOutput()
		done <- err
	}()

	select {
	case err := <-done:
		if err != nil {
			return string(output), fmt.Errorf("execution failed: %v", err)
		}
		return string(output), nil
	case <-time.After(time.Duration(timeout) * time.Second):
		if cmd.Process != nil {
			cmd.Process.Kill()
		}
		return "", fmt.Errorf("execution timed out after %d seconds", timeout)
	}
}

func executeTerminalCommand(command, workingDir string, timeout int) (string, error) {
	cmd := exec.Command("bash", "-c", command)

	if workingDir != "" {
		cmd.Dir = workingDir
	}

	done := make(chan error, 1)
	var output []byte

	go func() {
		var err error
		output, err = cmd.CombinedOutput()
		done <- err
	}()

	select {
	case err := <-done:
		if err != nil {
			return string(output), fmt.Errorf("command failed: %v", err)
		}
		return string(output), nil
	case <-time.After(time.Duration(timeout) * time.Second):
		if cmd.Process != nil {
			cmd.Process.Kill()
		}
		return "", fmt.Errorf("command timed out after %d seconds", timeout)
	}
}

func evaluateExpression(expression, language string) (string, error) {
	switch strings.ToLower(language) {
	case "python":
		code := fmt.Sprintf("print(%s)", expression)
		return executeCode(code, "python", 10)
	case "javascript", "js":
		code := fmt.Sprintf("console.log(%s)", expression)
		return executeCode(code, "javascript", 10)
	case "go":
		code := fmt.Sprintf(`package main
import "fmt"
func main() {
	fmt.Println(%s)
}`, expression)
		return executeCode(code, "go", 10)
	default:
		if num, err := strconv.ParseFloat(expression, 64); err == nil {
			return fmt.Sprintf("%g", num), nil
		}
		return "", fmt.Errorf("unsupported language for expression evaluation: %s", language)
	}
}

func GetExecutionTools() []tools.Tool {
	return []tools.Tool{
		RunCodeTool{},
		ExecuteTerminalTool{},
		EvaluateExpressionTool{},
	}
}
