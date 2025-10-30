'use client';

import { useState } from 'react';
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { 
  Sparkles, 
  MessageSquare, 
  Bell, 
  Plus,
  ChevronRight,
  X,
  Wallet,
  Copy,
  ExternalLink
} from "lucide-react";
import { usePathname } from 'next/navigation';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [walletAddress] = useState('0x742d...92a8');
  const [walletBalance] = useState('9.99');
  const [notifications, setNotifications] = useState([
    { id: 1, type: 'success', title: 'Agent Started', message: 'Your agent is now running', unread: true },
    { id: 2, type: 'info', title: 'New Feature', message: 'Voice input is now available', unread: true },
    { id: 3, type: 'warning', title: 'Low Balance', message: 'Your balance is running low', unread: false },
    { id: 4, type: 'success', title: 'Task Completed', message: 'Smart contract deployed successfully', unread: false },
  ]);
  
  const pathname = usePathname();
  
  const unreadCount = notifications.filter(n => n.unread).length;
  
  const markAsRead = (id: number) => {
    setNotifications(notifications.map(n => 
      n.id === id ? { ...n, unread: false } : n
    ));
  };
  
  const markAllAsRead = () => {
    setNotifications(notifications.map(n => ({ ...n, unread: false })));
  };
  
  const removeNotification = (id: number) => {
    setNotifications(notifications.filter(n => n.id !== id));
  };

  const getBreadcrumb = () => {
    const path = pathname.split('/').filter(Boolean);
    if (path.length === 1) return 'Chat';
    return path[path.length - 1].charAt(0).toUpperCase() + path[path.length - 1].slice(1);
  };

  

  const recentChats = [
    { 
      id: 1, 
      title: 'Deploy smart contract', 
      preview: 'Create a liquidity pool smart contract and deploy it to Mezo testnet',
    },
    { 
      id: 2, 
      title: 'Explain Mezo architecture', 
      preview: 'How does the Bitcoin L2 layer work with Mezo protocol?',
    },
    { 
      id: 3, 
      title: 'Gas optimization tips', 
      preview: 'Best practices for reducing gas costs in smart contracts',

    },
    { 
      id: 4, 
      title: 'Python data analysis', 
      preview: 'Run analysis on blockchain transaction data',
    },
  ];

  return (
    <SidebarProvider>
      <div className="flex h-screen w-full bg-[#0F172A] text-white overflow-hidden">
        {/* Sidebar */}
        <Sidebar className="border-r border-white/10 bg-[#1e1b4b]" style={{ 
          '--sidebar-background': '#1e1b4b',
          '--sidebar-foreground': 'white',
          '--sidebar-primary': '#F7931A',
          '--sidebar-primary-foreground': 'white',
          '--sidebar-accent': 'rgba(255, 255, 255, 0.05)',
          '--sidebar-accent-foreground': 'white',
          '--sidebar-border': 'rgba(255, 255, 255, 0.1)',
        } as React.CSSProperties}>
          {/* Logo Section */}
          <SidebarHeader className="border-b border-white/10 bg-[#1e1b4b]">
            <div className="flex items-center gap-3 px-4 py-4">
              <div className="w-10 h-10 bg-linear-to-br from-[#F7931A] to-[#FCD34D] rounded-lg flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="text-lg font-bold text-white">JARVIS</div>
                <div className="text-xs text-white/60">Your AI Agent</div>
              </div>
            </div>
          </SidebarHeader>

          <SidebarContent className="bg-[#1e1b4b]">
           
            {/* Recent Conversations */}
            <SidebarGroup className="bg-[#1e1b4b]">
              <SidebarGroupLabel className="text-xs font-semibold text-white/60 px-4 bg-[#1e1b4b]">
                RECENT CHATS
              </SidebarGroupLabel>
              <SidebarGroupContent className="bg-[#1e1b4b]">
                <SidebarMenu className="bg-[#1e1b4b]">
                  {recentChats.map((chat) => {
                    return (
                      <SidebarMenuItem key={chat.id} className="bg-[#1e1b4b]">
                        <SidebarMenuButton 
                          asChild 
                          className="text-white/60 hover:bg-white/5 hover:text-white bg-[#1e1b4b] h-auto py-2"
                          title={chat.preview}
                        >
                          <div className="flex items-start gap-2 cursor-pointer w-full">
                            <MessageSquare className="w-3.5 h-3.5 text-white/40 mt-0.5 shrink-0" />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-2 mb-0.5">
                                <div className="text-xs text-white/80 truncate font-medium">
                                  {chat.title}
                                </div>
                              </div>
                              <div className="text-[10px] text-white/40 truncate mb-1">
                                {chat.preview}
                              </div>

                            </div>
                          </div>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    );
                  })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>

          {/* Footer */}
          <SidebarFooter className="border-t border-white/10 bg-[#1e1b4b]">
            <div className="p-4">
              <Button 
                className="w-full bg-linear-to-r from-[#F7931A] to-[#F97316] hover:from-[#FCD34D] hover:to-[#F7931A] text-white font-semibold"
              >
                <Plus className="w-4 h-4 mr-2" />
                New Chat
              </Button>
            </div>
          </SidebarFooter>
        </Sidebar>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Navigation Bar */}
          <header className="h-16 border-b border-white/10 bg-[#1e1b4b]/50 backdrop-blur-sm flex items-center justify-between px-6">
            {/* Left: Sidebar Toggle & Breadcrumb */}
            <div className="flex items-center gap-4">
              <SidebarTrigger className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/60" />
              <div className="flex items-center gap-2 text-sm">
                <span className="text-white/60">Dashboard</span>
                <ChevronRight className="w-4 h-4 text-white/40" />
                <span className="text-white font-medium">{getBreadcrumb()}</span>
              </div>
            </div>

          {/* Right: Notifications & User */}
          <div className="flex items-center gap-4">
            {/* Wallet Section */}
            <div className="flex items-center gap-2 bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg px-4 py-2 hover:bg-white/10 transition-colors cursor-pointer group">
              <Wallet className="w-4 h-4 text-[#FCD34D]" />
              <div className="flex flex-col">
                <div className="text-[10px] text-white/40 uppercase tracking-wide">Balance</div>
                <div className="text-sm font-bold text-[#FCD34D]">{walletBalance} MEZO</div>
              </div>
              <div className="ml-2 pl-2 border-l border-white/20">
                <div className="text-xs text-white/60 font-mono flex items-center gap-1">
                  {walletAddress}
                  <button
                    onClick={() => navigator.clipboard.writeText('0x742d35a9f1234567890abcdef1234567890192a8')}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                    title="Copy full address"
                  >
                    <Copy className="w-3 h-3 text-white/40 hover:text-white" />
                  </button>
                  <button
                    onClick={() => window.open('https://explorer.mezo.io', '_blank')}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                    title="View on explorer"
                  >
                    <ExternalLink className="w-3 h-3 text-white/40 hover:text-white" />
                  </button>
                </div>
              </div>
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="relative p-2 hover:bg-white/10 rounded-lg transition-colors">
                  <Bell className="w-5 h-5 text-white/60" />
                  {unreadCount > 0 && (
                    <div className="absolute top-1 right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
                      <span className="text-[10px] font-bold text-white">{unreadCount}</span>
                    </div>
                  )}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-80 bg-[#1e1b4b] border-white/10">
                <DropdownMenuLabel className="flex items-center justify-between">
                  <span className="text-white">Notifications</span>
                  {unreadCount > 0 && (
                    <button 
                      onClick={markAllAsRead}
                      className="text-xs text-[#F7931A] hover:text-[#FCD34D] transition-colors"
                    >
                      Mark all as read
                    </button>
                  )}
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-white/10" />
                
                {notifications.length === 0 ? (
                  <div className="px-2 py-8 text-center text-white/40 text-sm">
                    No notifications
                  </div>
                ) : (
                  <div className="max-h-[400px] overflow-y-auto">
                    {notifications.map((notification) => (
                      <DropdownMenuItem 
                        key={notification.id}
                        className="flex items-start gap-3 px-3 py-3 cursor-pointer focus:bg-white/5 hover:bg-white/5"
                        onClick={() => markAsRead(notification.id)}
                      >
                        <div className={`shrink-0 w-2 h-2 rounded-full mt-1.5 ${
                          notification.type === 'success' ? 'bg-green-500' :
                          notification.type === 'warning' ? 'bg-yellow-500' :
                          notification.type === 'error' ? 'bg-red-500' :
                          'bg-blue-500'
                        } ${notification.unread ? 'animate-pulse' : 'opacity-50'}`}></div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <div className={`text-sm font-medium ${notification.unread ? 'text-white' : 'text-white/60'}`}>
                              {notification.title}
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                removeNotification(notification.id);
                              }}
                              className="shrink-0 p-1 hover:bg-white/10 rounded transition-colors"
                            >
                              <X className="w-3 h-3 text-white/40 hover:text-white/80" />
                            </button>
                          </div>
                          <p className={`text-xs mt-1 ${notification.unread ? 'text-white/60' : 'text-white/40'}`}>
                            {notification.message}
                          </p>
                        </div>
                      </DropdownMenuItem>
                    ))}
                  </div>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page Content */}
        {children}
      </div>
      </div>
    </SidebarProvider>
  );
}
