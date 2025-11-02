package repository

import (
	"context"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"

	"jarvis/api/data"
)

type InvoiceRepository struct {
	*BaseRepository[*data.Invoice]
}

func NewInvoiceRepository(db *mongo.Database) *InvoiceRepository {
	return &InvoiceRepository{
		BaseRepository: NewBaseRepository[*data.Invoice](db, "invoices"),
	}
}

func (r *InvoiceRepository) GetByUserID(ctx context.Context, userID string) ([]*data.Invoice, error) {
	filter := bson.M{"user_id": userID}
	return r.FindBy(ctx, filter)
}

func (r *InvoiceRepository) GetByUserIDAndMonth(ctx context.Context, userID string, month, year int) (*data.Invoice, error) {
	filter := bson.M{
		"user_id": userID,
		"month":   month,
		"year":    year,
	}
	return r.FindOneBy(ctx, filter)
}

func (r *InvoiceRepository) GetUnpaidInvoices(ctx context.Context) ([]*data.Invoice, error) {
	filter := bson.M{"is_paid": false}
	return r.FindBy(ctx, filter)
}

func (r *InvoiceRepository) GetPaidInvoices(ctx context.Context) ([]*data.Invoice, error) {
	filter := bson.M{"is_paid": true}
	return r.FindBy(ctx, filter)
}

func (r *InvoiceRepository) MarkAsPaid(ctx context.Context, invoiceID string) error {
	invoice := &data.Invoice{ID: invoiceID}
	now := time.Now()
	updateFields := bson.M{
		"is_paid": true,
		"paid_at": now,
	}
	return r.BaseRepository.Update(ctx, invoice, updateFields)
}

func (r *InvoiceRepository) Update(ctx context.Context, invoice *data.Invoice) error {
	updateFields := bson.M{
		"user_id":                invoice.UserID,
		"month":                  invoice.Month,
		"year":                   invoice.Year,
		"amount":                 invoice.Amount,
		"payment_validation_url": invoice.PaymentValidationUrl,
		"is_paid":                invoice.IsPaid,
	}
	if invoice.PaidAt != nil {
		updateFields["paid_at"] = invoice.PaidAt
	}
	return r.BaseRepository.Update(ctx, invoice, updateFields)
}
