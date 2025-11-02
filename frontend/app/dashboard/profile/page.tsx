'use client';

import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { 
  User, 
  Mail, 
  Calendar,
  Shield,
  Save,
  Loader2,
  CheckCircle,
  Clock,
  Receipt,
  DollarSign,
  AlertCircle,
  CheckCircle2,
  CreditCard,
  RefreshCw,
  FileText
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiClient } from "@/lib/api-client";
import type { AuthResponse, Invoice } from "@/lib/api-client";
import { toast } from "sonner";

export default function ProfilePage() {
  const [profile, setProfile] = useState<AuthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [invoicesLoading, setInvoicesLoading] = useState(true);
  const [payingInvoices, setPayingInvoices] = useState<Set<string>>(new Set());
  const [formData, setFormData] = useState({
    username: '',
    email: '',
  });

  useEffect(() => {
    fetchProfile();
    fetchInvoices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const data = await apiClient.users.getProfile();
      setProfile(data);
      setFormData({
        username: data.username,
        email: data.email,
      });
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      toast.error('Failed to load profile', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const updatedProfile = await apiClient.users.updateProfile({
        username: formData.username,
        email: formData.email,
      });
      setProfile(updatedProfile);
      
      if (typeof window !== 'undefined') {
        localStorage.setItem('user', JSON.stringify(updatedProfile));
      }
      
      toast.success('Profile updated successfully', {
        description: 'Your changes have been saved',
      });
    } catch (error) {
      console.error('Failed to update profile:', error);
      toast.error('Failed to update profile', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const fetchInvoices = async () => {
    try {
      setInvoicesLoading(true);
      
      // Try to fetch real invoices first
      try {
        const data = await apiClient.invoices.getAll();
        const sorted = data.sort((a, b) => {
          if (a.is_paid !== b.is_paid) {
            return a.is_paid ? 1 : -1;
          }
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
        setInvoices(sorted);
      } catch {
        // If API call fails, use mock data to demonstrate frontend capabilities
        console.log('Using mock invoice data for demonstration');
        const mockInvoices: Invoice[] = [
          {
            id: '67890abc-1234-5678-90ab-cdef12345678',
            user_id: profile?.user_id || 'demo-user',
            month: 11,
            year: 2025,
            amount: 49.99,
            transaction_hash: 'https://payment.example.com/invoice/nov-2025',
            is_paid: false,
            created_at: new Date(2025, 10, 1).toISOString(),
            last_active: new Date(2025, 10, 1).toISOString(),
          },
          {
            id: '12345def-6789-0abc-def1-234567890abc',
            user_id: profile?.user_id || 'demo-user',
            month: 10,
            year: 2025,
            amount: 45.00,
            transaction_hash: 'https://payment.example.com/invoice/oct-2025',
            is_paid: true,
            created_at: new Date(2025, 9, 1).toISOString(),
            last_active: new Date(2025, 9, 1).toISOString(),
            paid_at: new Date(2025, 9, 15).toISOString(),
          },
          {
            id: 'abcdef12-3456-7890-abcd-ef1234567890',
            user_id: profile?.user_id || 'demo-user',
            month: 9,
            year: 2025,
            amount: 52.50,
            transaction_hash: 'https://payment.example.com/invoice/sep-2025',
            is_paid: true,
            created_at: new Date(2025, 8, 1).toISOString(),
            last_active: new Date(2025, 8, 1).toISOString(),
            paid_at: new Date(2025, 8, 10).toISOString(),
          },
          {
            id: '567890ab-cdef-1234-5678-90abcdef1234',
            user_id: profile?.user_id || 'demo-user',
            month: 8,
            year: 2025,
            amount: 38.75,
            transaction_hash: 'https://payment.example.com/invoice/aug-2025',
            is_paid: true,
            created_at: new Date(2025, 7, 1).toISOString(),
            last_active: new Date(2025, 7, 1).toISOString(),
            paid_at: new Date(2025, 7, 20).toISOString(),
          },
          {
            id: '90abcdef-1234-5678-90ab-cdef12345678',
            user_id: profile?.user_id || 'demo-user',
            month: 7,
            year: 2025,
            amount: 41.25,
            transaction_hash: 'https://payment.example.com/invoice/jul-2025',
            is_paid: false,
            created_at: new Date(2025, 6, 1).toISOString(),
            last_active: new Date(2025, 6, 1).toISOString(),
          },
          {
            id: 'cdef1234-5678-90ab-cdef-1234567890ab',
            user_id: profile?.user_id || 'demo-user',
            month: 6,
            year: 2025,
            amount: 47.80,
            transaction_hash: 'https://payment.example.com/invoice/jun-2025',
            is_paid: true,
            created_at: new Date(2025, 5, 1).toISOString(),
            last_active: new Date(2025, 5, 1).toISOString(),
            paid_at: new Date(2025, 5, 18).toISOString(),
          },
        ];
        
        const sorted = mockInvoices.sort((a, b) => {
          if (a.is_paid !== b.is_paid) {
            return a.is_paid ? 1 : -1;
          }
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
        setInvoices(sorted);
        
        toast.info('Displaying demo invoices', {
          description: 'These are sample invoices to demonstrate the interface',
        });
      }
    } catch (error) {
      console.error('Failed to fetch invoices:', error);
      toast.error('Failed to load invoices', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setInvoicesLoading(false);
    }
  };

  const handlePayInvoice = async (invoiceId: string) => {
    try {
      setPayingInvoices(prev => new Set(prev).add(invoiceId));
      const updatedInvoice = await apiClient.invoices.checkPayment(invoiceId);
      
      setInvoices(prev => prev.map(inv => 
        inv.id === invoiceId ? updatedInvoice : inv
      ));

      if (updatedInvoice.is_paid) {
        toast.success('Payment verified!', {
          description: 'Your invoice has been marked as paid',
        });
      } else {
        toast.warning('Payment not found', {
          description: 'Please complete the payment and try again',
        });
      }
    } catch (error) {
      console.error('Failed to check payment:', error);
      toast.error('Failed to verify payment', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setPayingInvoices(prev => {
        const newSet = new Set(prev);
        newSet.delete(invoiceId);
        return newSet;
      });
    }
  };

  const formatMonth = (month: number, year: number) => {
    const date = new Date(year, month - 1);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
    });
  };

  const getInvoiceStats = () => {
    const unpaid = invoices.filter(inv => !inv.is_paid);
    const paid = invoices.filter(inv => inv.is_paid);
    const totalUnpaid = unpaid.reduce((sum, inv) => sum + inv.amount, 0);
    const totalPaid = paid.reduce((sum, inv) => sum + inv.amount, 0);
    
    return { unpaid: unpaid.length, paid: paid.length, totalUnpaid, totalPaid };
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-[#F7931A] animate-spin" />
          <p className="text-white/60">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Profile & Billing</h1>
            <p className="text-white/60">Manage your account information, preferences, and billing</p>
          </div>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="profile" className="w-full">
          <TabsList className="grid w-full grid-cols-2 bg-white/5 border border-white/10">
            <TabsTrigger 
              value="profile" 
              className="data-[state=active]:bg-[#F7931A] data-[state=active]:text-white text-white/60"
            >
              <User className="w-4 h-4 mr-2" />
              Profile & Account
            </TabsTrigger>
            <TabsTrigger 
              value="billing" 
              className="data-[state=active]:bg-[#F7931A] data-[state=active]:text-white text-white/60"
            >
              <Receipt className="w-4 h-4 mr-2" />
              Billing & Invoices
            </TabsTrigger>
          </TabsList>

          {/* Profile Tab Content */}
          <TabsContent value="profile" className="space-y-6 mt-6">
            {/* Profile Information Card */}
            <Card className="bg-[#1e1b4b]/50 border-white/10 p-6">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-20 h-20 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-full flex items-center justify-center">
                  <User className="w-10 h-10 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">{profile?.username}</h2>
                  <p className="text-white/60">{profile?.email}</p>
                </div>
              </div>

              <div className="space-y-4">
                {/* Username Field */}
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-white/80 flex items-center gap-2">
                    <User className="w-4 h-4" />
                    Username
                  </Label>
                  <Input
                    id="username"
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    className="bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-[#F7931A]/50 h-12"
                    placeholder="Enter username"
                  />
                </div>

                {/* Email Field */}
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-white/80 flex items-center gap-2">
                    <Mail className="w-4 h-4" />
                    Email Address
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="bg-white/5 border-white/10 text-white placeholder:text-white/40 focus:border-[#F7931A]/50 h-12"
                    placeholder="Enter email"
                  />
                </div>

                {/* Save Button */}
                <div className="pt-4">
                  <Button
                    onClick={handleSave}
                    disabled={saving || (formData.username === profile?.username && formData.email === profile?.email)}
                    className="bg-linear-to-r from-[#F7931A] to-[#F97316] hover:from-[#FCD34D] hover:to-[#F7931A] text-white font-semibold h-12 px-8"
                  >
                    {saving ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        Save Changes
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </Card>

            {/* Account Details Card */}
            <Card className="bg-[#1e1b4b]/50 border-white/10 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5 text-[#F7931A]" />
                Account Details
              </h3>

              <div className="space-y-4">
                {/* User ID */}
                <div className="flex items-center justify-between py-3 border-b border-white/10">
                  <div className="flex items-center gap-2 text-white/60">
                    <Shield className="w-4 h-4" />
                    <span>User ID</span>
                  </div>
                  <span className="text-white/80 font-mono text-sm">{profile?.user_id}</span>
                </div>

                {/* Container ID */}
                <div className="flex items-center justify-between py-3 border-b border-white/10">
                  <div className="flex items-center gap-2 text-white/60">
                    <Shield className="w-4 h-4" />
                    <span>Container ID</span>
                  </div>
                  <span className="text-white/80 font-mono text-sm">{profile?.container_id}</span>
                </div>

                {/* Created At */}
                <div className="flex items-center justify-between py-3 border-b border-white/10">
                  <div className="flex items-center gap-2 text-white/60">
                    <Calendar className="w-4 h-4" />
                    <span>Account Created</span>
                  </div>
                  <span className="text-white/80 text-sm">{formatDate(profile?.created_at)}</span>
                </div>

                {/* Last Active */}
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-2 text-white/60">
                    <Clock className="w-4 h-4" />
                    <span>Last Active</span>
                  </div>
                  <span className="text-white/80 text-sm">{formatDate(profile?.last_active)}</span>
                </div>

                {/* Account Status */}
                {profile && 'is_active' in profile && (
                  <div className="flex items-center justify-between py-3 pt-4 border-t border-white/10">
                    <div className="flex items-center gap-2 text-white/60">
                      <CheckCircle className="w-4 h-4" />
                      <span>Account Status</span>
                    </div>
                    <span className={`text-sm font-medium ${profile.is_active ? 'text-green-400' : 'text-red-400'}`}>
                      {profile.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                )}
              </div>
            </Card>

            {/* Security Notice */}
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-blue-400 mt-0.5" />
                <div>
                  <h4 className="text-sm font-medium text-blue-200 mb-1">Security Notice</h4>
                  <p className="text-xs text-blue-300/80">
                    Your account is secured with JWT authentication. Keep your credentials safe and log out from shared devices.
                  </p>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Billing Tab Content */}
          <TabsContent value="billing" className="space-y-6 mt-6">
            <Card className="bg-[#1e1b4b]/50 border-white/10 p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                    <Receipt className="w-5 h-5 text-[#F7931A]" />
                    Billing & Invoices
                  </h3>
                  <p className="text-sm text-white/40 mt-1">View and manage your billing history</p>
                </div>
                <Button
                  onClick={fetchInvoices}
                  variant="outline"
                  size="sm"
                  className="border-white/10 hover:bg-white/5"
                >
                  <RefreshCw className="w-3 h-3 mr-2" />
                  Refresh
                </Button>
              </div>

              {invoicesLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-[#F7931A] animate-spin" />
                </div>
              ) : invoices.length === 0 ? (
                <div className="flex flex-col items-center justify-center text-center py-12">
                  <Receipt className="w-16 h-16 text-white/20 mb-4" />
                  <h4 className="text-lg font-medium text-white mb-2">No invoices yet</h4>
                  <p className="text-sm text-white/40">Your invoices will appear here when they are generated</p>
                </div>
              ) : (
                <>
                  {/* Stats Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertCircle className="w-5 h-5 text-red-400" />
                        <span className="text-sm text-red-300 font-medium">Unpaid</span>
                      </div>
                      <p className="text-2xl font-bold text-red-400 mb-1">{getInvoiceStats().unpaid}</p>
                      <p className="text-xs text-red-300/60">${getInvoiceStats().totalUnpaid.toFixed(2)} due</p>
                    </div>
                    
                    <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <CheckCircle2 className="w-5 h-5 text-green-400" />
                        <span className="text-sm text-green-300 font-medium">Paid</span>
                      </div>
                      <p className="text-2xl font-bold text-green-400 mb-1">{getInvoiceStats().paid}</p>
                      <p className="text-xs text-green-300/60">${getInvoiceStats().totalPaid.toFixed(2)} paid</p>
                    </div>
                    
                    <div className="bg-[#F7931A]/10 border border-[#F7931A]/20 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Receipt className="w-5 h-5 text-[#F7931A]" />
                        <span className="text-sm text-[#FCD34D] font-medium">Total</span>
                      </div>
                      <p className="text-2xl font-bold text-white mb-1">{invoices.length}</p>
                      <p className="text-xs text-white/40">${(getInvoiceStats().totalPaid + getInvoiceStats().totalUnpaid).toFixed(2)} total</p>
                    </div>

                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <DollarSign className="w-5 h-5 text-blue-400" />
                        <span className="text-sm text-blue-300 font-medium">Average</span>
                      </div>
                      <p className="text-2xl font-bold text-blue-400 mb-1">
                        ${invoices.length > 0 ? ((getInvoiceStats().totalPaid + getInvoiceStats().totalUnpaid) / invoices.length).toFixed(2) : '0.00'}
                      </p>
                      <p className="text-xs text-blue-300/60">per invoice</p>
                    </div>
                  </div>

                  {/* Invoices List */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-white/80">Invoice History</h4>
                      <span className="text-xs text-white/40">{invoices.length} invoice{invoices.length !== 1 ? 's' : ''}</span>
                    </div>
                    
                    <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                      {invoices.map((invoice) => (
                        <div
                          key={invoice.id}
                          className={`border rounded-lg p-5 transition-all hover:shadow-lg ${
                            invoice.is_paid
                              ? 'bg-white/5 border-white/10 hover:border-white/20'
                              : 'bg-red-500/5 border-red-500/30 border-l-4 border-l-red-500 hover:border-red-500/40'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 space-y-3">
                              {/* Invoice Header */}
                              <div className="flex items-center gap-3">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                  invoice.is_paid ? 'bg-green-500/20' : 'bg-red-500/20'
                                }`}>
                                  {invoice.is_paid ? (
                                    <CheckCircle2 className="w-5 h-5 text-green-400" />
                                  ) : (
                                    <AlertCircle className="w-5 h-5 text-red-400" />
                                  )}
                                </div>
                                <div className="flex-1">
                                  <div className="flex items-center gap-2">
                                    <h4 className="text-base font-semibold text-white">
                                      {formatMonth(invoice.month, invoice.year)}
                                    </h4>
                                    <Badge 
                                      variant={invoice.is_paid ? "default" : "destructive"}
                                      className={`text-xs ${invoice.is_paid ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30' : ''}`}
                                    >
                                      {invoice.is_paid ? 'Paid' : 'Unpaid'}
                                    </Badge>
                                  </div>
                                  <p className="text-xs text-white/40 mt-0.5">Invoice #{invoice.id.slice(0, 12)}...</p>
                                </div>
                              </div>

                              {/* Invoice Details */}
                              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pl-13">
                                <div className="flex items-center gap-2">
                                  <DollarSign className="w-4 h-4 text-white/40" />
                                  <div>
                                    <p className="text-xs text-white/40">Amount</p>
                                    <p className="text-sm font-semibold text-white">${invoice.amount.toFixed(2)}</p>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2">
                                  <Calendar className="w-4 h-4 text-white/40" />
                                  <div>
                                    <p className="text-xs text-white/40">Issued</p>
                                    <p className="text-sm text-white/70">{new Date(invoice.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</p>
                                  </div>
                                </div>

                                {invoice.is_paid && invoice.paid_at && (
                                  <div className="flex items-center gap-2">
                                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                                    <div>
                                      <p className="text-xs text-white/40">Paid On</p>
                                      <p className="text-sm text-green-400">{new Date(invoice.paid_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</p>
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Payment URL */}
                              {invoice.transaction_hash && (
                                <div className="flex items-start gap-2 pl-13 pt-2 border-t border-white/10">
                                  <FileText className="w-4 h-4 text-white/40 mt-0.5" />
                                  <div className="flex-1 min-w-0">
                                    <p className="text-xs text-white/40 mb-1">Payment URL</p>
                                    <a
                                      href={invoice.transaction_hash}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-xs text-[#F7931A] hover:text-[#FCD34D] transition-colors font-mono truncate block"
                                    >
                                      {invoice.transaction_hash}
                                    </a>
                                  </div>
                                </div>
                              )}
                            </div>

                            {/* Action Buttons */}
                            <div className="flex flex-col gap-2">
                              {!invoice.is_paid ? (
                                <>
                                  <Button
                                    onClick={() => handlePayInvoice(invoice.id)}
                                    disabled={payingInvoices.has(invoice.id)}
                                    size="sm"
                                    className="bg-linear-to-r from-[#F7931A] to-[#F97316] hover:from-[#FCD34D] hover:to-[#F7931A] text-white text-xs font-semibold whitespace-nowrap"
                                  >
                                    {payingInvoices.has(invoice.id) ? (
                                      <>
                                        <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                                        Checking...
                                      </>
                                    ) : (
                                      <>
                                        <CreditCard className="w-3 h-3 mr-1.5" />
                                        Pay Now
                                      </>
                                    )}
                                  </Button>
                                </>
                              ) : (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  disabled
                                  className="border-green-500/20 bg-green-500/5 text-green-400 text-xs whitespace-nowrap cursor-not-allowed"
                                >
                                  <CheckCircle2 className="w-3 h-3 mr-1.5" />
                                  Paid
                                </Button>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Info Notice */}
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mt-6">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-blue-400 mt-0.5 shrink-0" />
                      <div>
                        <h4 className="text-sm font-medium text-blue-200 mb-1">About Invoices</h4>
                        <p className="text-xs text-blue-300/80">
                          Invoices are generated monthly for your usage. Click &quot;Pay Now&quot; on unpaid invoices to verify payment and update the invoice status.
                          You cannot delete invoices, but you can view your complete payment history here.
                        </p>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
