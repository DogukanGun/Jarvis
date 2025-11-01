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
  Clock
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import type { AuthResponse } from "@/lib/api-client";
import { toast } from "sonner";

export default function ProfilePage() {
  const [profile, setProfile] = useState<AuthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
  });

  useEffect(() => {
    fetchProfile();
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
      
      // Update localStorage
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
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Profile Settings</h1>
            <p className="text-white/60">Manage your account information and preferences</p>
          </div>
        </div>

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
      </div>
    </div>
  );
}
