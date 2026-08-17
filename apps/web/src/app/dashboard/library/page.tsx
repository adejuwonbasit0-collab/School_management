'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format, isPast } from 'date-fns';
import {
  Library, Plus, Search, BookOpen, Users, AlertCircle, CheckCircle2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

export default function LibraryPage() {
  const [search, setSearch] = useState('');
  const [addBookOpen, setAddBookOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [isbn, setIsbn] = useState('');
  const [category, setCategory] = useState('');
  const [quantity, setQuantity] = useState(1);
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  const { data: library } = useQuery({
    queryKey: ['library'],
    queryFn: () => api.get<any>('/v1/library'),
  });

  const { data: items, isLoading } = useQuery({
    queryKey: ['library-items', search],
    queryFn: () => api.get<any>('/v1/library/items', { search, limit: 50 }),
  });

  const { data: activeBorrows } = useQuery({
    queryKey: ['active-borrows'],
    queryFn: () => api.get<any>('/v1/library/borrows/active'),
  });

  const addBookMutation = useMutation({
    mutationFn: () => api.post('/v1/library/items', { title, author, isbn, category, quantity }),
    onSuccess: () => {
      toast.success('Book added to library');
      qc.invalidateQueries({ queryKey: ['library-items'] });
      qc.invalidateQueries({ queryKey: ['library'] });
      setAddBookOpen(false);
      setTitle(''); setAuthor(''); setIsbn(''); setCategory(''); setQuantity(1);
    },
  });

  const returnMutation = useMutation({
    mutationFn: (borrowId: string) => api.put(`/v1/library/borrow/${borrowId}/return`, {}),
    onSuccess: (data: any) => {
      toast.success(data.fine > 0 ? `Book returned. Fine: ₦${data.fine}` : 'Book returned successfully');
      qc.invalidateQueries({ queryKey: ['active-borrows'] });
      qc.invalidateQueries({ queryKey: ['library-items'] });
    },
  });

  const books = items?.data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">Library</h1>
          <p className="section-subtitle">{library?.name || 'School Library'}</p>
        </div>
        {hasPermission('library:library:CREATE') && (
          <Button size="sm" onClick={() => setAddBookOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />Add Book
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <div className="inline-flex p-2 rounded-lg bg-blue-50 dark:bg-blue-950/30 mb-2"><BookOpen className="w-4 h-4 text-blue-600" /></div>
          <p className="text-2xl font-bold">{library?._count?.items || 0}</p>
          <p className="text-xs text-muted-foreground">Total Titles</p>
        </CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <div className="inline-flex p-2 rounded-lg bg-amber-50 dark:bg-amber-950/30 mb-2"><Users className="w-4 h-4 text-amber-600" /></div>
          <p className="text-2xl font-bold">{activeBorrows?.length || 0}</p>
          <p className="text-xs text-muted-foreground">Active Borrows</p>
        </CardContent></Card>
        <Card className="shadow-card"><CardContent className="pt-4 pb-4">
          <div className="inline-flex p-2 rounded-lg bg-red-50 dark:bg-red-950/30 mb-2"><AlertCircle className="w-4 h-4 text-red-600" /></div>
          <p className="text-2xl font-bold">{(activeBorrows || []).filter((b: any) => isPast(new Date(b.dueDate))).length}</p>
          <p className="text-xs text-muted-foreground">Overdue</p>
        </CardContent></Card>
      </div>

      <Tabs defaultValue="catalog">
        <TabsList>
          <TabsTrigger value="catalog">Catalog</TabsTrigger>
          <TabsTrigger value="borrows">Active Borrows</TabsTrigger>
        </TabsList>

        <TabsContent value="catalog" className="space-y-4 mt-4">
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Search by title, author, ISBN..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>

          <Card className="data-table-container shadow-card">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead>Title</TableHead>
                  <TableHead>Author</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>ISBN</TableHead>
                  <TableHead>Available</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading
                  ? Array.from({ length: 6 }).map((_, i) => <TableRow key={i}>{Array.from({ length: 6 }).map((_, j) => <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>)}</TableRow>)
                  : books.length === 0
                  ? <TableRow><TableCell colSpan={6} className="text-center py-12 text-muted-foreground"><BookOpen className="w-10 h-10 mx-auto mb-2 opacity-20" />No books in catalog</TableCell></TableRow>
                  : books.map((book: any) => (
                      <TableRow key={book.id} className="hover:bg-muted/30">
                        <TableCell className="font-medium text-sm">{book.title}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{book.author || '—'}</TableCell>
                        <TableCell><Badge variant="outline" className="text-xs">{book.category || 'General'}</Badge></TableCell>
                        <TableCell className="text-xs font-mono text-muted-foreground">{book.isbn || '—'}</TableCell>
                        <TableCell className="text-sm">{book.available}/{book.quantity}</TableCell>
                        <TableCell>
                          <Badge variant="secondary" className={book.available > 0 ? 'badge-success' : 'badge-danger'}>
                            {book.available > 0 ? 'Available' : 'All Borrowed'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        <TabsContent value="borrows" className="mt-4">
          <Card className="data-table-container shadow-card">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead>Student</TableHead>
                  <TableHead>Book</TableHead>
                  <TableHead>Borrowed</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-24"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(activeBorrows || []).length === 0
                  ? <TableRow><TableCell colSpan={6} className="text-center py-12 text-muted-foreground">No active borrows</TableCell></TableRow>
                  : (activeBorrows || []).map((b: any) => {
                      const overdue = isPast(new Date(b.dueDate));
                      return (
                        <TableRow key={b.id} className="hover:bg-muted/30">
                          <TableCell className="text-sm font-medium">{b.student?.user?.firstName} {b.student?.user?.lastName}</TableCell>
                          <TableCell className="text-sm">{b.item?.title}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">{format(new Date(b.borrowedAt), 'dd MMM yyyy')}</TableCell>
                          <TableCell className="text-sm">{format(new Date(b.dueDate), 'dd MMM yyyy')}</TableCell>
                          <TableCell>
                            <Badge variant="secondary" className={overdue ? 'badge-danger' : 'badge-success'}>
                              {overdue ? 'Overdue' : 'On Time'}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Button size="sm" variant="outline" onClick={() => returnMutation.mutate(b.id)}>
                              <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />Return
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Add Book Dialog */}
      <Dialog open={addBookOpen} onOpenChange={setAddBookOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Add Book to Library</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5"><Label>Title *</Label><Input value={title} onChange={(e) => setTitle(e.target.value)} /></div>
            <div className="space-y-1.5"><Label>Author</Label><Input value={author} onChange={(e) => setAuthor(e.target.value)} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>ISBN</Label><Input value={isbn} onChange={(e) => setIsbn(e.target.value)} /></div>
              <div className="space-y-1.5"><Label>Category</Label><Input value={category} onChange={(e) => setCategory(e.target.value)} /></div>
            </div>
            <div className="space-y-1.5"><Label>Quantity</Label><Input type="number" value={quantity} onChange={(e) => setQuantity(parseInt(e.target.value) || 1)} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddBookOpen(false)}>Cancel</Button>
            <Button disabled={!title || addBookMutation.isPending} onClick={() => addBookMutation.mutate()}>
              {addBookMutation.isPending ? 'Adding...' : 'Add Book'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
