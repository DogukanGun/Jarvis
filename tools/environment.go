package jarvisTools

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
	"time"

	"github.com/tmc/langchaingo/tools"
)

type InstallPackageTool struct{}

func (t InstallPackageTool) Name() string {
	return "install_package"
}

func (t InstallPackageTool) Description() string {
	return "Install packages using various package managers (npm, pip, go get, etc.). Input should be JSON with 'package_name', 'package_manager', optional 'version', and optional 'global' fields."
}

func (t InstallPackageTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		PackageName    string `json:"package_name"`
		PackageManager string `json:"package_manager"`
		Version        string `json:"version"`
		Global         bool   `json:"global"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	return installPackage(args.PackageName, args.PackageManager, args.Version, args.Global)
}

type CheckVersionTool struct{}

func (t CheckVersionTool) Name() string {
	return "check_version"
}

func (t CheckVersionTool) Description() string {
	return "Check the version of installed tools and packages. Input should be JSON with 'tool_name' field."
}

func (t CheckVersionTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		ToolName string `json:"tool_name"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	return checkVersion(args.ToolName)
}

type LintCodeTool struct{}

func (t LintCodeTool) Name() string {
	return "lint_code"
}

func (t LintCodeTool) Description() string {
	return "Run linting tools on code files. Input should be JSON with 'file_path', 'language', and optional 'linter' fields."
}

func (t LintCodeTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		FilePath string `json:"file_path"`
		Language string `json:"language"`
		Linter   string `json:"linter"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	return lintCode(args.FilePath, args.Language, args.Linter)
}

func installPackage(packageName, packageManager, version string, global bool) (string, error) {
	var cmd *exec.Cmd

	switch strings.ToLower(packageManager) {
	case "npm":
		args := []string{"install"}
		if global {
			args = append(args, "-g")
		}
		if version != "" {
			packageName = fmt.Sprintf("%s@%s", packageName, version)
		}
		args = append(args, packageName)
		cmd = exec.Command("npm", args...)

	case "pip", "pip3":
		args := []string{"install"}
		if version != "" {
			packageName = fmt.Sprintf("%s==%s", packageName, version)
		}
		args = append(args, packageName)
		cmd = exec.Command("pip3", args...)

	case "go":
		args := []string{"get"}
		if version != "" {
			packageName = fmt.Sprintf("%s@%s", packageName, version)
		}
		args = append(args, packageName)
		cmd = exec.Command("go", args...)

	case "cargo":
		args := []string{"install"}
		if version != "" {
			args = append(args, "--vers", version)
		}
		args = append(args, packageName)
		cmd = exec.Command("cargo", args...)

	case "yarn":
		args := []string{"add"}
		if global {
			args = append(args, "global")
		}
		if version != "" {
			packageName = fmt.Sprintf("%s@%s", packageName, version)
		}
		args = append(args, packageName)
		cmd = exec.Command("yarn", args...)

	default:
		return "", fmt.Errorf("unsupported package manager: %s", packageManager)
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
			return string(output), fmt.Errorf("package installation failed: %v", err)
		}
		return string(output), nil
	case <-time.After(5 * time.Minute):
		if cmd.Process != nil {
			cmd.Process.Kill()
		}
		return "", fmt.Errorf("package installation timed out")
	}
}

func checkVersion(toolName string) (string, error) {
	var cmd *exec.Cmd

	switch strings.ToLower(toolName) {
	case "go":
		cmd = exec.Command("go", "version")
	case "python", "python3":
		cmd = exec.Command("python3", "--version")
	case "node", "nodejs":
		cmd = exec.Command("node", "--version")
	case "npm":
		cmd = exec.Command("npm", "--version")
	case "yarn":
		cmd = exec.Command("yarn", "--version")
	case "cargo":
		cmd = exec.Command("cargo", "--version")
	case "rust", "rustc":
		cmd = exec.Command("rustc", "--version")
	case "git":
		cmd = exec.Command("git", "--version")
	case "docker":
		cmd = exec.Command("docker", "--version")
	default:
		cmd = exec.Command(toolName, "--version")
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("failed to check version of %s: %v", toolName, err)
	}

	return strings.TrimSpace(string(output)), nil
}

func lintCode(filePath, language, linter string) (string, error) {
	var cmd *exec.Cmd

	switch strings.ToLower(language) {
	case "go":
		if linter == "" {
			linter = "golint"
		}
		switch linter {
		case "golint":
			cmd = exec.Command("golint", filePath)
		case "gofmt":
			cmd = exec.Command("gofmt", "-d", filePath)
		case "govet":
			cmd = exec.Command("go", "vet", filePath)
		case "staticcheck":
			cmd = exec.Command("staticcheck", filePath)
		default:
			return "", fmt.Errorf("unsupported Go linter: %s", linter)
		}

	case "python":
		if linter == "" {
			linter = "flake8"
		}
		switch linter {
		case "flake8":
			cmd = exec.Command("flake8", filePath)
		case "pylint":
			cmd = exec.Command("pylint", filePath)
		case "black":
			cmd = exec.Command("black", "--check", filePath)
		default:
			return "", fmt.Errorf("unsupported Python linter: %s", linter)
		}

	case "javascript", "js":
		if linter == "" {
			linter = "eslint"
		}
		switch linter {
		case "eslint":
			cmd = exec.Command("eslint", filePath)
		case "jshint":
			cmd = exec.Command("jshint", filePath)
		case "prettier":
			cmd = exec.Command("prettier", "--check", filePath)
		default:
			return "", fmt.Errorf("unsupported JavaScript linter: %s", linter)
		}

	case "typescript", "ts":
		if linter == "" {
			linter = "eslint"
		}
		switch linter {
		case "eslint":
			cmd = exec.Command("eslint", filePath)
		case "tslint":
			cmd = exec.Command("tslint", filePath)
		case "prettier":
			cmd = exec.Command("prettier", "--check", filePath)
		default:
			return "", fmt.Errorf("unsupported TypeScript linter: %s", linter)
		}

	default:
		return "", fmt.Errorf("unsupported language for linting: %s", language)
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		return string(output), fmt.Errorf("linting failed: %v", err)
	}

	if len(output) == 0 {
		return "No linting issues found", nil
	}

	return string(output), nil
}

func GetEnvironmentTools() []tools.Tool {
	return []tools.Tool{
		InstallPackageTool{},
		CheckVersionTool{},
		LintCodeTool{},
	}
}
