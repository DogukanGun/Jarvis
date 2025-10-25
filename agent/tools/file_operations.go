package jarvisTools

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"

	"github.com/tmc/langchaingo/tools"
)

type ReadFileTool struct{}

func (t ReadFileTool) Name() string {
	return "read_file"
}

func (t ReadFileTool) Description() string {
	return "Read the contents of a file from the filesystem. Input should be JSON with 'file_path' field."
}

func (t ReadFileTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		FilePath string `json:"file_path"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	content, err := ioutil.ReadFile(args.FilePath)
	if err != nil {
		return "", fmt.Errorf("failed to read file: %v", err)
	}

	return string(content), nil
}

type WriteFileTool struct{}

func (t WriteFileTool) Name() string {
	return "write_file"
}

func (t WriteFileTool) Description() string {
	return "Write content to a file on the filesystem. Input should be JSON with 'file_path' and 'content' fields."
}

func (t WriteFileTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		FilePath string `json:"file_path"`
		Content  string `json:"content"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	err := os.MkdirAll(filepath.Dir(args.FilePath), 0755)
	if err != nil {
		return "", fmt.Errorf("failed to create directory: %v", err)
	}

	err = ioutil.WriteFile(args.FilePath, []byte(args.Content), 0644)
	if err != nil {
		return "", fmt.Errorf("failed to write file: %v", err)
	}

	return fmt.Sprintf("Successfully wrote %d bytes to %s", len(args.Content), args.FilePath), nil
}

type DeleteFileTool struct{}

func (t DeleteFileTool) Name() string {
	return "delete_file"
}

func (t DeleteFileTool) Description() string {
	return "Delete a file from the filesystem. Input should be JSON with 'file_path' field."
}

func (t DeleteFileTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		FilePath string `json:"file_path"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	err := os.Remove(args.FilePath)
	if err != nil {
		return "", fmt.Errorf("failed to delete file: %v", err)
	}

	return fmt.Sprintf("Successfully deleted %s", args.FilePath), nil
}

type ListFilesTool struct{}

func (t ListFilesTool) Name() string {
	return "list_files"
}

func (t ListFilesTool) Description() string {
	return "List files and directories in a given path. Input should be JSON with 'directory_path' field and optional 'recursive' boolean."
}

func (t ListFilesTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		DirectoryPath string `json:"directory_path"`
		Recursive     bool   `json:"recursive"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	var files []string

	if args.Recursive {
		err := filepath.Walk(args.DirectoryPath, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return err
			}
			files = append(files, path)
			return nil
		})
		if err != nil {
			return "", fmt.Errorf("failed to walk directory: %v", err)
		}
	} else {
		entries, err := ioutil.ReadDir(args.DirectoryPath)
		if err != nil {
			return "", fmt.Errorf("failed to read directory: %v", err)
		}

		for _, entry := range entries {
			files = append(files, filepath.Join(args.DirectoryPath, entry.Name()))
		}
	}

	return strings.Join(files, "\n"), nil
}

func GetFileTools() []tools.Tool {
	return []tools.Tool{
		ReadFileTool{},
		WriteFileTool{},
		DeleteFileTool{},
		ListFilesTool{},
	}
}
