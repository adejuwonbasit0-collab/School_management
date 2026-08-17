'use client';
import { FileText } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
export default function AssignmentsPage() {
  return (
    <div className="space-y-6">
      <div><h1 className="section-title">Assignments</h1><p className="section-subtitle">Manage student assignments and submissions</p></div>
      <Card><CardContent className="py-16 text-center text-muted-foreground">
        <FileText className="w-12 h-12 mx-auto mb-3 opacity-20" />
        <p className="font-medium">Assignment module coming in Phase 2</p>
        <p className="text-sm mt-1">Create, assign, and grade student assignments</p>
      </CardContent></Card>
    </div>
  );
}
