package services

import (
	"context"
	"fmt"
	"time"

	"jarvis/api/data"
	"jarvis/api/repository"
)

type InvoiceManager struct {
	repository *repository.InvoiceRepository
}

func NewInvoiceManager(repo *repository.InvoiceRepository) *InvoiceManager {
	return &InvoiceManager{
		repository: repo,
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

	// Check payment validation URL
	isPaid, err := im.checkPaymentStatus(invoice.PaymentValidationUrl)
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

// checkPaymentStatus checks if payment is confirmed via the validation URL
func (im *InvoiceManager) checkPaymentStatus(validationUrl string) (bool, error) {
	// TODO: Implement payment validation logic
	return false, fmt.Errorf("payment validation not implemented yet")
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
