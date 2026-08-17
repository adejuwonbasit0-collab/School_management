'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Bot, Zap, BookOpen, ClipboardList, BarChart2, TrendingUp,
  FileText, MessageSquare, Loader2, Send, Sparkles, Settings,
  GraduationCap, Brain, Wand2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import api from '@/lib/api-client';
import { useAuth } from '@/store/auth.store';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';

const AI_MODULES = [
  { key: 'tutor', name: 'AI Tutor', icon: GraduationCap, desc: 'Answer student questions on any subject', color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-950/30' },
  { key: 'question-generator', name: 'Question Generator', icon: ClipboardList, desc: 'Auto-generate exam questions by topic', color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-950/30' },
  { key: 'lesson-planner', name: 'Lesson Planner', icon: BookOpen, desc: 'Generate detailed lesson plans', color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
  { key: 'result-analyzer', name: 'Result Analyzer', icon: BarChart2, desc: 'AI insights from exam results', color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-950/30' },
  { key: 'performance-predictor', name: 'Performance Predictor', icon: TrendingUp, desc: 'Predict student academic outcomes', color: 'text-red-600', bg: 'bg-red-50 dark:bg-red-950/30' },
  { key: 'report-writer', name: 'Report Writer', icon: FileText, desc: 'Auto-generate student terminal reports', color: 'text-teal-600', bg: 'bg-teal-50 dark:bg-teal-950/30' },
  { key: 'chat-assistant', name: 'AI Assistant', icon: MessageSquare, desc: 'General-purpose school AI assistant', color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-950/30' },
];

interface Message { role: 'user' | 'assistant'; content: string }

export default function AiCenterPage() {
  const { hasPermission } = useAuth();
  const qc = useQueryClient();

  // Tutor state
  const [tutorQuestion, setTutorQuestion] = useState('');
  const [tutorSubject, setTutorSubject] = useState('');
  const [tutorAnswer, setTutorAnswer] = useState('');

  // Question generator state
  const [qSubject, setQSubject] = useState('');
  const [qTopic, setQTopic] = useState('');
  const [qLevel, setQLevel] = useState('SS2');
  const [qCount, setQCount] = useState(5);
  const [qType, setQType] = useState('multiple_choice');
  const [qDifficulty, setQDifficulty] = useState('medium');
  const [questions, setQuestions] = useState<any[]>([]);

  // Lesson planner state
  const [lpSubject, setLpSubject] = useState('');
  const [lpTopic, setLpTopic] = useState('');
  const [lpLevel, setLpLevel] = useState('SS1');
  const [lpDuration, setLpDuration] = useState(45);
  const [lessonPlan, setLessonPlan] = useState<any>(null);

  // Chat state
  const [chatMessages, setChatMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState('');

  const { data: modules } = useQuery({
    queryKey: ['ai-modules'],
    queryFn: () => api.get<any>('/v1/ai/modules'),
  });

  const toggleModule = useMutation({
    mutationFn: ({ module, isEnabled }: { module: string; isEnabled: boolean }) =>
      api.post(`/v1/ai/modules/${module}/toggle`, { isEnabled }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ai-modules'] });
      toast.success('AI module updated');
    },
  });

  const isEnabled = (key: string) => (modules || []).find((m: any) => m.module === key)?.isEnabled;

  const tutorMutation = useMutation({
    mutationFn: () => api.post<any>('/v1/ai/tutor', { question: tutorQuestion, subject: tutorSubject }),
    onSuccess: (data: any) => setTutorAnswer(data.answer || data.error || ''),
    onError: () => toast.error('AI Tutor failed. Check if OpenAI API key is configured.'),
  });

  const qGenMutation = useMutation({
    mutationFn: () => api.post<any>('/v1/ai/questions/generate', {
      subject: qSubject, topic: qTopic, level: qLevel,
      count: qCount, type: qType, difficulty: qDifficulty,
    }),
    onSuccess: (data: any) => setQuestions(data.questions || []),
    onError: () => toast.error('Question generation failed'),
  });

  const lpMutation = useMutation({
    mutationFn: () => api.post<any>('/v1/ai/lesson-plan', {
      subject: lpSubject, topic: lpTopic, level: lpLevel, duration: lpDuration,
    }),
    onSuccess: (data: any) => setLessonPlan(data),
    onError: () => toast.error('Lesson plan generation failed'),
  });

  const chatMutation = useMutation({
    mutationFn: (messages: Message[]) => api.post<any>('/v1/ai/chat', { messages }),
    onSuccess: (data: any) => {
      setChatMessages((prev) => [...prev, { role: 'assistant', content: data.reply || data.error || '' }]);
    },
  });

  const sendChat = () => {
    if (!chatInput.trim()) return;
    const newMessages: Message[] = [...chatMessages, { role: 'user', content: chatInput }];
    setChatMessages(newMessages);
    setChatInput('');
    chatMutation.mutate(newMessages);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="section-title">AI Center</h1>
          <p className="section-subtitle">AI-powered tools for teaching and administration</p>
        </div>
        <Badge variant="secondary" className="gap-1.5 py-1 px-3">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          Powered by GPT-4o
        </Badge>
      </div>

      <Tabs defaultValue="modules">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="modules"><Settings className="w-3.5 h-3.5 mr-1.5" />Modules</TabsTrigger>
          <TabsTrigger value="tutor"><GraduationCap className="w-3.5 h-3.5 mr-1.5" />Tutor</TabsTrigger>
          <TabsTrigger value="questions"><ClipboardList className="w-3.5 h-3.5 mr-1.5" />Questions</TabsTrigger>
          <TabsTrigger value="lesson-plan"><BookOpen className="w-3.5 h-3.5 mr-1.5" />Lesson Plan</TabsTrigger>
          <TabsTrigger value="chat"><MessageSquare className="w-3.5 h-3.5 mr-1.5" />Assistant</TabsTrigger>
        </TabsList>

        {/* Module Management */}
        <TabsContent value="modules" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {AI_MODULES.map((mod) => {
              const Icon = mod.icon;
              const enabled = isEnabled(mod.key);
              return (
                <motion.div key={mod.key} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
                  <Card className={cn('shadow-card border-2 transition-colors', enabled ? 'border-primary/30' : 'border-transparent')}>
                    <CardContent className="pt-5 pb-5">
                      <div className="flex items-start justify-between mb-3">
                        <div className={cn('p-2.5 rounded-xl', mod.bg)}>
                          <Icon className={cn('w-5 h-5', mod.color)} />
                        </div>
                        {hasPermission('ai:ai:MANAGE') && (
                          <Switch
                            checked={enabled ?? false}
                            onCheckedChange={(v) => toggleModule.mutate({ module: mod.key, isEnabled: v })}
                          />
                        )}
                      </div>
                      <h3 className="font-semibold text-sm mb-1">{mod.name}</h3>
                      <p className="text-xs text-muted-foreground">{mod.desc}</p>
                      <div className="mt-3">
                        <Badge variant="secondary" className={cn('text-xs', enabled ? 'badge-success' : 'badge-neutral')}>
                          {enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            ⚠️ AI features require an OpenAI API key configured in your environment. Each request incurs API costs.
          </p>
        </TabsContent>

        {/* AI Tutor */}
        <TabsContent value="tutor" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Ask the AI Tutor</CardTitle>
                <CardDescription>Get detailed explanations on any academic topic</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>Subject (optional)</Label>
                    <Input value={tutorSubject} onChange={(e) => setTutorSubject(e.target.value)} placeholder="Mathematics" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Level</Label>
                    <Select onValueChange={() => {}}>
                      <SelectTrigger><SelectValue placeholder="SS2" /></SelectTrigger>
                      <SelectContent>
                        {['JSS1','JSS2','JSS3','SS1','SS2','SS3'].map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label>Your Question *</Label>
                  <Textarea
                    value={tutorQuestion}
                    onChange={(e) => setTutorQuestion(e.target.value)}
                    placeholder="Explain the quadratic formula and when to use it..."
                    rows={4}
                  />
                </div>
                <Button
                  className="w-full"
                  disabled={!tutorQuestion || tutorMutation.isPending || !isEnabled('tutor')}
                  onClick={() => tutorMutation.mutate()}
                >
                  {tutorMutation.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Thinking...</> : <><Sparkles className="w-4 h-4 mr-2" />Get Answer</>}
                </Button>
                {!isEnabled('tutor') && (
                  <p className="text-xs text-amber-600 text-center">Enable AI Tutor in the Modules tab first</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Answer</CardTitle>
              </CardHeader>
              <CardContent>
                {tutorAnswer ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed">
                    <ReactMarkdown>{tutorAnswer}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-40 text-muted-foreground">
                    <Brain className="w-12 h-12 opacity-20 mb-3" />
                    <p className="text-sm">Ask a question to get started</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Question Generator */}
        <TabsContent value="questions" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Generate Questions</CardTitle>
                <CardDescription>AI-powered exam question generation</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>Subject *</Label>
                    <Input value={qSubject} onChange={(e) => setQSubject(e.target.value)} placeholder="Mathematics" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Topic *</Label>
                    <Input value={qTopic} onChange={(e) => setQTopic(e.target.value)} placeholder="Quadratic Equations" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Level</Label>
                    <Select defaultValue="SS2" onValueChange={setQLevel}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {['JSS1','JSS2','JSS3','SS1','SS2','SS3'].map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Count</Label>
                    <Input type="number" min={1} max={20} value={qCount} onChange={(e) => setQCount(parseInt(e.target.value) || 5)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Question Type</Label>
                    <Select defaultValue="multiple_choice" onValueChange={setQType}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="multiple_choice">Multiple Choice</SelectItem>
                        <SelectItem value="true_false">True / False</SelectItem>
                        <SelectItem value="short_answer">Short Answer</SelectItem>
                        <SelectItem value="essay">Essay</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Difficulty</Label>
                    <Select defaultValue="medium" onValueChange={setQDifficulty}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="easy">Easy</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="hard">Hard</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <Button
                  className="w-full"
                  disabled={!qSubject || !qTopic || qGenMutation.isPending || !isEnabled('question-generator')}
                  onClick={() => qGenMutation.mutate()}
                >
                  {qGenMutation.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating...</> : <><Wand2 className="w-4 h-4 mr-2" />Generate Questions</>}
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2 flex-row items-center justify-between">
                <CardTitle className="text-base">Generated Questions</CardTitle>
                {questions.length > 0 && (
                  <Button variant="outline" size="sm" onClick={() => {
                    const text = questions.map((q, i) => `${i + 1}. ${q.question}\n${q.options?.map((o: string) => `   ${o}`).join('\n') || ''}\nAnswer: ${q.answer}\n`).join('\n');
                    navigator.clipboard.writeText(text);
                    toast.success('Copied to clipboard');
                  }}>Copy All</Button>
                )}
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px] pr-2">
                  {questions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-muted-foreground">
                      <ClipboardList className="w-12 h-12 opacity-20 mb-3" />
                      <p className="text-sm">Questions will appear here</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {questions.map((q, i) => (
                        <div key={i} className="border rounded-lg p-3">
                          <p className="font-medium text-sm mb-2">{i + 1}. {q.question}</p>
                          {q.options && (
                            <ul className="space-y-1 mb-2">
                              {q.options.map((opt: string, j: number) => (
                                <li key={j} className="text-xs text-muted-foreground">{opt}</li>
                              ))}
                            </ul>
                          )}
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="badge-success text-xs">Answer: {q.answer}</Badge>
                            {q.marks && <Badge variant="outline" className="text-xs">{q.marks} marks</Badge>}
                          </div>
                          {q.explanation && <p className="text-xs text-muted-foreground mt-2 italic">{q.explanation}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Lesson Plan */}
        <TabsContent value="lesson-plan" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Generate Lesson Plan</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>Subject *</Label>
                    <Input value={lpSubject} onChange={(e) => setLpSubject(e.target.value)} placeholder="Biology" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Topic *</Label>
                    <Input value={lpTopic} onChange={(e) => setLpTopic(e.target.value)} placeholder="Photosynthesis" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Level</Label>
                    <Select defaultValue="SS1" onValueChange={setLpLevel}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {['JSS1','JSS2','JSS3','SS1','SS2','SS3'].map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Duration (minutes)</Label>
                    <Input type="number" value={lpDuration} onChange={(e) => setLpDuration(parseInt(e.target.value) || 45)} />
                  </div>
                </div>
                <Button
                  className="w-full"
                  disabled={!lpSubject || !lpTopic || lpMutation.isPending || !isEnabled('lesson-planner')}
                  onClick={() => lpMutation.mutate()}
                >
                  {lpMutation.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating...</> : <><BookOpen className="w-4 h-4 mr-2" />Generate Lesson Plan</>}
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Lesson Plan</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px] pr-2">
                  {!lessonPlan ? (
                    <div className="flex flex-col items-center justify-center h-40 text-muted-foreground">
                      <BookOpen className="w-12 h-12 opacity-20 mb-3" />
                      <p className="text-sm">Lesson plan will appear here</p>
                    </div>
                  ) : (
                    <div className="space-y-3 text-sm">
                      <div className="bg-muted/50 rounded-lg p-3">
                        <p className="font-semibold">{lessonPlan.title}</p>
                        <p className="text-muted-foreground text-xs">{lessonPlan.subject} • {lessonPlan.level} • {lessonPlan.duration} mins</p>
                      </div>
                      {lessonPlan.objectives?.length > 0 && (
                        <div>
                          <p className="font-semibold mb-1">Learning Objectives</p>
                          <ul className="list-disc list-inside space-y-0.5 text-muted-foreground text-xs">
                            {lessonPlan.objectives.map((o: string, i: number) => <li key={i}>{o}</li>)}
                          </ul>
                        </div>
                      )}
                      {lessonPlan.introduction && (
                        <div>
                          <p className="font-semibold mb-1">Introduction ({lessonPlan.introduction.duration} min)</p>
                          <ul className="list-disc list-inside space-y-0.5 text-muted-foreground text-xs">
                            {lessonPlan.introduction.activities?.map((a: string, i: number) => <li key={i}>{a}</li>)}
                          </ul>
                        </div>
                      )}
                      {lessonPlan.mainLesson && (
                        <div>
                          <p className="font-semibold mb-1">Main Lesson ({lessonPlan.mainLesson.duration} min)</p>
                          <ul className="list-disc list-inside space-y-0.5 text-muted-foreground text-xs">
                            {lessonPlan.mainLesson.teachingPoints?.map((p: string, i: number) => <li key={i}>{p}</li>)}
                          </ul>
                        </div>
                      )}
                      {lessonPlan.homework && (
                        <div className="border-t pt-3">
                          <p className="font-semibold mb-1">Homework</p>
                          <p className="text-xs text-muted-foreground">{lessonPlan.homework}</p>
                        </div>
                      )}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* AI Chat */}
        <TabsContent value="chat" className="mt-4">
          <Card className="h-[600px] flex flex-col">
            <CardHeader className="pb-3 flex-shrink-0">
              <CardTitle className="text-base flex items-center gap-2">
                <Bot className="w-5 h-5 text-primary" /> EduCore AI Assistant
              </CardTitle>
              <CardDescription>Ask anything about school management, curriculum, or administration</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col min-h-0 p-0">
              <ScrollArea className="flex-1 px-4">
                <div className="space-y-4 py-4">
                  {chatMessages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                      <MessageSquare className="w-12 h-12 opacity-20 mb-3" />
                      <p className="text-sm">Start a conversation with EduCore AI</p>
                      <div className="flex flex-wrap gap-2 mt-4 justify-center">
                        {['How do I add a student?', 'Generate a fee report', 'What are the top performing classes?'].map((s) => (
                          <button
                            key={s}
                            onClick={() => setChatInput(s)}
                            className="text-xs border rounded-full px-3 py-1 hover:bg-muted transition-colors"
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {chatMessages.map((msg, i) => (
                    <div key={i} className={cn('flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
                      <div className={cn(
                        'max-w-[80%] rounded-2xl px-4 py-2.5 text-sm',
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground rounded-br-sm'
                          : 'bg-muted text-foreground rounded-bl-sm',
                      )}>
                        {msg.role === 'assistant'
                          ? <div className="prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown>{msg.content}</ReactMarkdown></div>
                          : msg.content}
                      </div>
                    </div>
                  ))}
                  {chatMutation.isPending && (
                    <div className="flex justify-start">
                      <div className="bg-muted rounded-2xl rounded-bl-sm px-4 py-3">
                        <div className="flex gap-1">
                          {[0, 1, 2].map((i) => (
                            <div key={i} className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </ScrollArea>

              <div className="flex gap-2 p-4 border-t flex-shrink-0">
                <Input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask anything..."
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendChat()}
                  disabled={!isEnabled('chat-assistant') || chatMutation.isPending}
                  className="flex-1"
                />
                <Button
                  onClick={sendChat}
                  disabled={!chatInput.trim() || !isEnabled('chat-assistant') || chatMutation.isPending}
                  size="icon"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
              {!isEnabled('chat-assistant') && (
                <p className="text-xs text-amber-600 text-center pb-2">Enable AI Assistant in the Modules tab</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
