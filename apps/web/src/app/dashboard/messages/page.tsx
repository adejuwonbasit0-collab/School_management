'use client';
import { MessageSquare } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
export default function MessagesPage() {
  return (
    <div className="space-y-6">
      <div><h1 className="section-title">Messages</h1><p className="section-subtitle">Internal messaging system</p></div>
      <Card><CardContent className="py-16 text-center text-muted-foreground">
        <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-20" />
        <p className="font-medium">Messaging module coming in Phase 2</p>
        <p className="text-sm mt-1">Direct messaging between staff, students, and parents</p>
      </CardContent></Card>
    </div>
  );
}
