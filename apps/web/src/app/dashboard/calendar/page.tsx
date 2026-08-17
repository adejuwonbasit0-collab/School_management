'use client';
import { useQuery } from '@tanstack/react-query';
import { format, endOfMonth, eachDayOfInterval, isToday, isSameMonth } from 'date-fns';
import { useState } from 'react';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api-client';
import { cn } from '@/lib/utils';

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const { data: events } = useQuery({
    queryKey: ['events'],
    queryFn: () => api.get<any>('/v1/cms/events'),
  });

  const startOfMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth(), 1);
  const parseISO = (value: string) => new Date(value);
  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const days = eachDayOfInterval({ start: monthStart, end: monthEnd });
  const eventList = events || [];

  const getEventsForDay = (day: Date) =>
    eventList.filter((e: any) => format(parseISO(e.startDate), 'yyyy-MM-dd') === format(day, 'yyyy-MM-dd'));

  return (
    <div className="space-y-6">
      <div><h1 className="section-title">School Calendar</h1><p className="section-subtitle">Events, holidays and important dates</p></div>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{format(currentDate, 'MMMM yyyy')}</CardTitle>
            <div className="flex gap-1">
              <Button variant="ghost" size="icon" className="w-8 h-8" onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1))}><ChevronLeft className="w-4 h-4" /></Button>
              <Button variant="ghost" size="sm" className="text-xs" onClick={() => setCurrentDate(new Date())}>Today</Button>
              <Button variant="ghost" size="icon" className="w-8 h-8" onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1))}><ChevronRight className="w-4 h-4" /></Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-7 gap-px bg-border rounded-lg overflow-hidden">
            {['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map((d) => (
              <div key={d} className="bg-muted/50 text-center text-xs font-medium text-muted-foreground py-2">{d}</div>
            ))}
            {Array.from({ length: monthStart.getDay() }).map((_, i) => (
              <div key={`empty-${i}`} className="bg-background h-24" />
            ))}
            {days.map((day) => {
              const dayEvents = getEventsForDay(day);
              return (
                <div key={day.toString()} className={cn('bg-background h-24 p-1.5 hover:bg-muted/30 transition-colors', isToday(day) && 'bg-primary/5 border border-primary/30')}>
                  <p className={cn('text-xs font-medium w-6 h-6 flex items-center justify-center rounded-full', isToday(day) && 'bg-primary text-white')}>{format(day, 'd')}</p>
                  <div className="mt-1 space-y-0.5">
                    {dayEvents.slice(0, 2).map((e: any) => (
                      <div key={e.id} className="text-xs bg-blue-100 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400 rounded px-1 truncate">{e.title}</div>
                    ))}
                    {dayEvents.length > 2 && <div className="text-xs text-muted-foreground">+{dayEvents.length - 2} more</div>}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {eventList.length > 0 && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-base">Upcoming Events</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {eventList.slice(0, 10).map((e: any) => (
              <div key={e.id} className="flex items-start gap-3 border-b last:border-0 pb-3">
                <div className="text-center bg-primary/10 rounded-lg p-2 w-12 shrink-0">
                  <p className="text-xs font-medium text-primary">{format(parseISO(e.startDate), 'MMM')}</p>
                  <p className="text-lg font-bold text-primary">{format(parseISO(e.startDate), 'd')}</p>
                </div>
                <div>
                  <p className="font-medium text-sm">{e.title}</p>
                  {e.location && <p className="text-xs text-muted-foreground">{e.location}</p>}
                  {e.description && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{e.description}</p>}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
