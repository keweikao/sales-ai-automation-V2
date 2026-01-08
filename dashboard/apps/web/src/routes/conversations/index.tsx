import { createFileRoute, Link } from '@tanstack/react-router';
import { useState } from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  StatusBadge,
  Select,
  Input,
  Button,
} from '@sales-ai/ui';
import type { ConversationStatus, ConversationFilters } from '@sales-ai/types';
import { useConversations } from '@/hooks/use-dashboard';

export const Route = createFileRoute('/conversations')({
  component: ConversationsPage,
});

const statusOptions = [
  { value: '', label: '全部狀態' },
  { value: 'pending', label: '待處理' },
  { value: 'transcribing', label: '轉錄中' },
  { value: 'analyzing', label: '分析中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失敗' },
];

function ConversationsPage() {
  const [filters, setFilters] = useState<ConversationFilters>({
    limit: 20,
    offset: 0,
  });

  const { data, isLoading } = useConversations(filters);

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const status = e.target.value as ConversationStatus | '';
    setFilters((prev) => ({
      ...prev,
      status: status || undefined,
      offset: 0,
    }));
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters((prev) => ({
      ...prev,
      salesRep: e.target.value || undefined,
      offset: 0,
    }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">對話記錄</h1>
        <p className="text-muted-foreground">查看和管理所有銷售對話</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 gap-4">
              <Input
                placeholder="搜尋業務員..."
                className="max-w-xs"
                onChange={handleSearchChange}
              />
              <Select
                options={statusOptions}
                value={filters.status || ''}
                onChange={handleStatusChange}
                className="w-40"
              />
            </div>
            <div className="text-sm text-muted-foreground">
              共 {data?.total ?? 0} 筆記錄
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-10">
              <div className="text-muted-foreground">載入中...</div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>業務員</TableHead>
                  <TableHead>類型</TableHead>
                  <TableHead>狀態</TableHead>
                  <TableHead>建立時間</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((conv) => (
                  <TableRow key={conv.id}>
                    <TableCell className="font-mono text-sm">{conv.id}</TableCell>
                    <TableCell>{conv.salesRepName || '-'}</TableCell>
                    <TableCell>
                      {conv.conversationType ? (
                        <span className="capitalize">{conv.conversationType}</span>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={conv.status} />
                    </TableCell>
                    <TableCell>
                      {new Date(conv.createdAt).toLocaleString('zh-TW')}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link
                        to="/conversations/$id"
                        params={{ id: conv.id }}
                        className="text-sm text-primary hover:underline"
                      >
                        查看詳情
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
                {(!data?.items || data.items.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      沒有找到對話記錄
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {data && data.total > (filters.limit || 20) && (
            <div className="mt-4 flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                顯示 {(filters.offset || 0) + 1} - {Math.min((filters.offset || 0) + (filters.limit || 20), data.total)} 筆
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={(filters.offset || 0) === 0}
                  onClick={() =>
                    setFilters((prev) => ({
                      ...prev,
                      offset: Math.max(0, (prev.offset || 0) - (prev.limit || 20)),
                    }))
                  }
                >
                  上一頁
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={(filters.offset || 0) + (filters.limit || 20) >= data.total}
                  onClick={() =>
                    setFilters((prev) => ({
                      ...prev,
                      offset: (prev.offset || 0) + (prev.limit || 20),
                    }))
                  }
                >
                  下一頁
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
