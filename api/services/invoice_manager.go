package services

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"

	"jarvis/api/data"
	"jarvis/api/repository"
)

type InvoiceManager struct {
	repository  *repository.InvoiceRepository
	userManager *UserManager
}

func NewInvoiceManager(repo *repository.InvoiceRepository, userManager *UserManager) *InvoiceManager {
	return &InvoiceManager{
		repository:  repo,
		userManager: userManager,
	}
}

// CreateInvoice creates a new invoice for a user
func (im *InvoiceManager) CreateInvoice(userID string, month, year int, amount float64, paymentValidationUrl string) (*data.Invoice, error) {
	ctx := context.Background()

	// Check if invoice already exists for this user and month/year
	existingInvoice, err := im.repository.GetByUserIDAndMonth(ctx, userID, month, year)
	if err == nil && existingInvoice != nil {
		return nil, fmt.Errorf("invoice already exists for user %s for %d/%d", userID, month, year)
	}

	invoice := &data.Invoice{
		UserID:               userID,
		Month:                month,
		Year:                 year,
		Amount:               amount,
		PaymentValidationUrl: paymentValidationUrl,
		IsPaid:               false,
		CreatedAt:            time.Now(),
		LastActive:           time.Now(),
	}

	if err := im.repository.Create(ctx, invoice); err != nil {
		return nil, fmt.Errorf("failed to create invoice: %w", err)
	}

	return invoice, nil
}

// CheckPaymentAndUpdate checks the payment validation URL and updates invoice status
func (im *InvoiceManager) CheckPaymentAndUpdate(invoiceID string) (*data.Invoice, error) {
	ctx := context.Background()

	// Get the invoice
	invoice, err := im.repository.GetByID(ctx, invoiceID)
	if err != nil {
		return nil, fmt.Errorf("failed to get invoice: %w", err)
	}

	// If already paid, return as is
	if invoice.IsPaid {
		return invoice, nil
	}

	// Check payment validation URL (txHash)
	isPaid, err := im.checkPaymentStatus(invoice.UserID, invoice.PaymentValidationUrl)
	if err != nil {
		return nil, fmt.Errorf("failed to check payment status: %w", err)
	}

	// Update invoice if payment is confirmed
	if isPaid {
		if err := im.repository.MarkAsPaid(ctx, invoiceID); err != nil {
			return nil, fmt.Errorf("failed to mark invoice as paid: %w", err)
		}
		// Refresh invoice data
		invoice, err = im.repository.GetByID(ctx, invoiceID)
		if err != nil {
			return nil, fmt.Errorf("failed to get updated invoice: %w", err)
		}
	}

	return invoice, nil
}

// GetUserUnpaidInvoices returns all unpaid invoices for a specific user
func (im *InvoiceManager) GetUserUnpaidInvoices(userID string) ([]*data.Invoice, error) {
	ctx := context.Background()

	// Get all user invoices
	allInvoices, err := im.repository.GetByUserID(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to get user invoices: %w", err)
	}

	// Filter unpaid invoices
	var unpaidInvoices []*data.Invoice
	for _, invoice := range allInvoices {
		if !invoice.IsPaid {
			unpaidInvoices = append(unpaidInvoices, invoice)
		}
	}

	return unpaidInvoices, nil
}

// GetUserInvoices returns all invoices for a specific user
func (im *InvoiceManager) GetUserInvoices(userID string) ([]*data.Invoice, error) {
	ctx := context.Background()
	return im.repository.GetByUserID(ctx, userID)
}

// GetInvoiceByID returns a specific invoice by ID
func (im *InvoiceManager) GetInvoiceByID(invoiceID string) (*data.Invoice, error) {
	ctx := context.Background()
	return im.repository.GetByID(ctx, invoiceID)
}

// GetAllUnpaidInvoices returns all unpaid invoices in the system
func (im *InvoiceManager) GetAllUnpaidInvoices() ([]*data.Invoice, error) {
	ctx := context.Background()
	return im.repository.GetUnpaidInvoices(ctx)
}

// GetAllPaidInvoices returns all paid invoices in the system
func (im *InvoiceManager) GetAllPaidInvoices() ([]*data.Invoice, error) {
	ctx := context.Background()
	return im.repository.GetPaidInvoices(ctx)
}

// UpdateInvoice updates an existing invoice
func (im *InvoiceManager) UpdateInvoice(invoice *data.Invoice) error {
	ctx := context.Background()
	return im.repository.Update(ctx, invoice)
}

// DeleteInvoice removes an invoice from the system
func (im *InvoiceManager) DeleteInvoice(invoiceID string) error {
	ctx := context.Background()
	return im.repository.Delete(ctx, invoiceID)
}

// checkPaymentStatus verifies transaction on Mezo testnet
func (im *InvoiceManager) checkPaymentStatus(userID string, txHash string) (bool, error) {
	// Get environment variables
	subsAmount := os.Getenv("SUBS_AMOUNT")
	hotWallet := os.Getenv("HOT_WALLET")

	if subsAmount == "" {
		return false, fmt.Errorf("SUBS_AMOUNT environment variable not set")
	}
	if hotWallet == "" {
		return false, fmt.Errorf("HOT_WALLET environment variable not set")
	}

	// Get user to get wallet address
	user, err := im.userManager.GetUser(userID)
	if err != nil {
		return false, fmt.Errorf("failed to get user: %w", err)
	}

	// Verify transaction
	return im.verifyMezoTransaction(txHash, user.WalletAddress, hotWallet, subsAmount)
}

// verifyMezoTransaction verifies a transaction on Mezo testnet
func (im *InvoiceManager) verifyMezoTransaction(txHash, userWallet, hotWallet, subsAmountStr string) (bool, error) {
	// Get transaction details
	tx, err := im.getMezoTransaction(txHash)
	if err != nil {
		return false, fmt.Errorf("failed to get transaction: %w", err)
	}

	// Verify transaction status
	if tx["status"] != "0x1" {
		return false, fmt.Errorf("transaction failed or pending")
	}

	// Verify sender is the user
	from, ok := tx["from"].(string)
	if !ok || from != userWallet {
		return false, fmt.Errorf("transaction sender does not match user wallet")
	}

	// Verify recipient is the hot wallet
	to, ok := tx["to"].(string)
	if !ok || to != hotWallet {
		return false, fmt.Errorf("transaction recipient does not match hot wallet")
	}

	// Convert expected amount to Wei
	expectedAmount, err := strconv.ParseFloat(subsAmountStr, 64)
	if err != nil {
		return false, fmt.Errorf("invalid SUBS_AMOUNT: %w", err)
	}
	expectedAmountWei := int64(expectedAmount * 1e18)

	// Convert transaction value from hex to int64
	value, ok := tx["value"].(string)
	if !ok {
		return false, fmt.Errorf("transaction value not found")
	}
	txValueWei, err := im.hexToInt64(value)
	if err != nil {
		return false, fmt.Errorf("failed to parse transaction value: %w", err)
	}

	// Verify amount
	if txValueWei < expectedAmountWei {
		return false, fmt.Errorf("transaction amount insufficient: got %d, expected %d", txValueWei, expectedAmountWei)
	}

	return true, nil
}

// getMezoTransaction retrieves transaction details from Mezo testnet
func (im *InvoiceManager) getMezoTransaction(txHash string) (map[string]interface{}, error) {
	rpcURL := "https://mezo-testnet.drpc.org"

	// Prepare RPC request for transaction
	request := map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  "eth_getTransactionByHash",
		"params":  []interface{}{txHash},
		"id":      1,
	}

	// Make RPC call
	txResp, err := im.makeRPCCall(rpcURL, request)
	if err != nil {
		return nil, fmt.Errorf("failed to get transaction: %w", err)
	}

	txData, ok := txResp["result"].(map[string]interface{})
	if !ok || txData == nil {
		return nil, fmt.Errorf("transaction not found")
	}

	// Get transaction receipt for status
	receiptRequest := map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  "eth_getTransactionReceipt",
		"params":  []interface{}{txHash},
		"id":      2,
	}

	receiptResp, err := im.makeRPCCall(rpcURL, receiptRequest)
	if err != nil {
		return nil, fmt.Errorf("failed to get transaction receipt: %w", err)
	}

	receiptData, ok := receiptResp["result"].(map[string]interface{})
	if !ok || receiptData == nil {
		return nil, fmt.Errorf("transaction receipt not found")
	}

	// Add status to transaction data
	if status, exists := receiptData["status"]; exists {
		txData["status"] = status
	}

	return txData, nil
}

// makeRPCCall makes an RPC call to the blockchain
func (im *InvoiceManager) makeRPCCall(rpcURL string, request map[string]interface{}) (map[string]interface{}, error) {
	requestBody, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Post(rpcURL, "application/json", bytes.NewBuffer(requestBody))
	if err != nil {
		return nil, fmt.Errorf("failed to make RPC call: %w", err)
	}
	defer func() {
		if err := resp.Body.Close(); err != nil {
			fmt.Printf("Error closing response body: %v\n", err)
		}
	}()

	var rpcResponse map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&rpcResponse); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	if errorField, exists := rpcResponse["error"]; exists && errorField != nil {
		return nil, fmt.Errorf("RPC error: %v", errorField)
	}

	return rpcResponse, nil
}

// hexToInt64 converts hex string to int64
func (im *InvoiceManager) hexToInt64(hexStr string) (int64, error) {
	if hexStr == "" {
		return 0, nil
	}

	if len(hexStr) > 2 && hexStr[:2] == "0x" {
		hexStr = hexStr[2:]
	}

	return strconv.ParseInt(hexStr, 16, 64)
}

// GenerateMonthlyInvoice creates a new monthly invoice for a specific user
func (im *InvoiceManager) GenerateMonthlyInvoice(userID string, month, year int, amount float64, paymentValidationUrl string) (*data.Invoice, error) {
	return im.CreateInvoice(userID, month, year, amount, paymentValidationUrl)
}

// GetInvoiceStatistics returns statistics about invoices
func (im *InvoiceManager) GetInvoiceStatistics() (map[string]interface{}, error) {
	ctx := context.Background()

	paidInvoices, err := im.repository.GetPaidInvoices(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get paid invoices: %w", err)
	}

	unpaidInvoices, err := im.repository.GetUnpaidInvoices(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get unpaid invoices: %w", err)
	}

	allInvoices, err := im.repository.GetAll(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get all invoices: %w", err)
	}

	var totalPaidAmount, totalUnpaidAmount, totalAmount float64
	for _, invoice := range allInvoices {
		totalAmount += invoice.Amount
		if invoice.IsPaid {
			totalPaidAmount += invoice.Amount
		} else {
			totalUnpaidAmount += invoice.Amount
		}
	}

	stats := map[string]interface{}{
		"total_invoices":      len(allInvoices),
		"paid_invoices":       len(paidInvoices),
		"unpaid_invoices":     len(unpaidInvoices),
		"total_amount":        totalAmount,
		"total_paid_amount":   totalPaidAmount,
		"total_unpaid_amount": totalUnpaidAmount,
		"payment_rate":        float64(len(paidInvoices)) / float64(len(allInvoices)) * 100,
	}

	return stats, nil
}
