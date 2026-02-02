package storage

import (
	"bytes"
	"context"
	"crypto/sha256"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"jarvis/agent/schemas/group"
)

// MinIOClient wraps the minio client for storage operations
type MinIOClient struct {
	client *minio.Client
	bucket string
}

// NewMinIOClient creates a new MinIO client
func NewMinIOClient() (*MinIOClient, error) {
	endpoint := os.Getenv("MINIO_ENDPOINT")
	if endpoint == "" {
		endpoint = "localhost:9000"
	}

	accessKey := os.Getenv("MINIO_ACCESS_KEY")
	if accessKey == "" {
		accessKey = "minioadmin"
	}

	secretKey := os.Getenv("MINIO_SECRET_KEY")
	if secretKey == "" {
		secretKey = "minioadmin"
	}

	useSSL := os.Getenv("MINIO_USE_SSL") == "true"

	bucket := os.Getenv("MINIO_BUCKET")
	if bucket == "" {
		bucket = "jarvis"
	}

	client, err := minio.New(endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(accessKey, secretKey, ""),
		Secure: useSSL,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create minio client: %v", err)
	}

	return &MinIOClient{
		client: client,
		bucket: bucket,
	}, nil
}

// EnsureBucket ensures the bucket exists, creating it if necessary
func (m *MinIOClient) EnsureBucket(ctx context.Context) error {
	exists, err := m.client.BucketExists(ctx, m.bucket)
	if err != nil {
		return fmt.Errorf("failed to check bucket existence: %v", err)
	}

	if !exists {
		if err := m.client.MakeBucket(ctx, m.bucket, minio.MakeBucketOptions{}); err != nil {
			return fmt.Errorf("failed to create bucket: %v", err)
		}
	}

	return nil
}

// UploadFile uploads a file and returns an ObjectRef
func (m *MinIOClient) UploadFile(ctx context.Context, filePath string, fileName string) (*group.ObjectRef, error) {
	if err := m.EnsureBucket(ctx); err != nil {
		return nil, err
	}

	file, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open file: %v", err)
	}
	defer file.Close()

	stat, err := file.Stat()
	if err != nil {
		return nil, fmt.Errorf("failed to stat file: %v", err)
	}

	// Generate key with timestamp for uniqueness
	key := fmt.Sprintf("%s/%d/%s", time.Now().Format("2006-01-02"), time.Now().UnixNano(), fileName)

	// Upload file
	info, err := m.client.PutObject(ctx, m.bucket, key, file, stat.Size(), minio.PutObjectOptions{
		ContentType: "application/octet-stream",
	})
	if err != nil {
		return nil, fmt.Errorf("failed to upload file: %v", err)
	}

	// Calculate SHA256
	file.Seek(0, 0)
	hash := sha256.New()
	if _, err := io.Copy(hash, file); err != nil {
		return nil, fmt.Errorf("failed to calculate hash: %v", err)
	}

	return &group.ObjectRef{
		Kind:   "minio",
		Bucket: m.bucket,
		Key:    key,
		ETag:   info.ETag,
		Size:   stat.Size(),
		SHA256: fmt.Sprintf("%x", hash.Sum(nil)),
	}, nil
}

// UploadBytes uploads bytes and returns an ObjectRef
func (m *MinIOClient) UploadBytes(ctx context.Context, data []byte, fileName string) (*group.ObjectRef, error) {
	if err := m.EnsureBucket(ctx); err != nil {
		return nil, err
	}

	// Generate key with timestamp for uniqueness
	key := fmt.Sprintf("%s/%d/%s", time.Now().Format("2006-01-02"), time.Now().UnixNano(), fileName)

	// Calculate SHA256
	hash := sha256.New()
	hash.Write(data)
	sha256Hex := fmt.Sprintf("%x", hash.Sum(nil))

	// Upload bytes
	info, err := m.client.PutObject(ctx, m.bucket, key, bytes.NewReader(data), int64(len(data)), minio.PutObjectOptions{
		ContentType: "application/octet-stream",
	})
	if err != nil {
		return nil, fmt.Errorf("failed to upload bytes: %v", err)
	}

	return &group.ObjectRef{
		Kind:   "minio",
		Bucket: m.bucket,
		Key:    key,
		ETag:   info.ETag,
		Size:   int64(len(data)),
		SHA256: sha256Hex,
	}, nil
}

// DownloadBytes downloads an object by key and returns the bytes
func (m *MinIOClient) DownloadBytes(ctx context.Context, key string) ([]byte, error) {
	obj, err := m.client.GetObject(ctx, m.bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get object: %v", err)
	}
	defer obj.Close()

	return io.ReadAll(obj)
}

// DownloadFile downloads an object to a file path
func (m *MinIOClient) DownloadFile(ctx context.Context, key string, filePath string) error {
	return m.client.FGetObject(ctx, m.bucket, key, filePath, minio.GetObjectOptions{})
}

// GetPresignedURL returns a presigned URL for downloading an object
func (m *MinIOClient) GetPresignedURL(ctx context.Context, key string, expiration time.Duration) (string, error) {
	url, err := m.client.PresignedGetObject(ctx, m.bucket, key, expiration, nil)
	if err != nil {
		return "", fmt.Errorf("failed to generate presigned URL: %v", err)
	}
	return url.String(), nil
}

// DeleteObject deletes an object
func (m *MinIOClient) DeleteObject(ctx context.Context, key string) error {
	return m.client.RemoveObject(ctx, m.bucket, key, minio.RemoveObjectOptions{})
}

// ObjectExists checks if an object exists
func (m *MinIOClient) ObjectExists(ctx context.Context, key string) (bool, error) {
	_, err := m.client.StatObject(ctx, m.bucket, key, minio.StatObjectOptions{})
	if err != nil {
		if minio.ToErrorResponse(err).Code == "NoSuchKey" {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

// ListObjects lists objects with a prefix
func (m *MinIOClient) ListObjects(ctx context.Context, prefix string) ([]minio.ObjectInfo, error) {
	var objects []minio.ObjectInfo
	for object := range m.client.ListObjects(ctx, m.bucket, minio.ListObjectsOptions{Prefix: prefix}) {
		if object.Err != nil {
			return nil, object.Err
		}
		objects = append(objects, object)
	}
	return objects, nil
}

// UploadFromObjectRef uploads from an ObjectRef (copy operation)
func (m *MinIOClient) CopyObject(ctx context.Context, srcRef *group.ObjectRef, destKey string) (*group.ObjectRef, error) {
	if err := m.EnsureBucket(ctx); err != nil {
		return nil, err
	}

	// Download from source
	data, err := m.DownloadBytes(ctx, srcRef.Key)
	if err != nil {
		return nil, fmt.Errorf("failed to download source object: %v", err)
	}

	// Upload to destination
	return m.UploadBytes(ctx, data, destKey)
}

// GetBucket returns the bucket name
func (m *MinIOClient) GetBucket() string {
	return m.bucket
}
