# Agent B: UI Components

## 任務說明

你是 UI Components Agent，負責將 UI 元件從舊專案遷移到新專案。

## 前置條件

- 專案 `/home/user/Sales_ai_automation_v3` 已建立
- `bun install` 已執行

## 任務清單

### 1. 檢查舊專案 UI 元件

讀取以下目錄了解現有元件：

```
/home/user/sales-ai-automation-V2/dashboard/packages/ui/src/
/home/user/sales-ai-automation-V2/dashboard/apps/web/src/components/
```

### 2. 複製並調整 UI 元件

將元件複製到 `/home/user/Sales_ai_automation_v3/packages/ui/src/`

需要調整：
- Import paths
- 確保使用 React 18+ 語法
- 確保符合 Biome 格式

### 3. 建立核心元件（如果不存在）

確保以下元件存在：

#### button.tsx
```typescript
import * as React from 'react'
import { cn } from '../lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive'
  size?: 'default' | 'sm' | 'lg'
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    return (
      <button
        className={cn(
          'inline-flex items-center justify-center rounded-md font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          {
            'bg-primary text-primary-foreground hover:bg-primary/90': variant === 'default',
            'border border-input bg-background hover:bg-accent': variant === 'outline',
            'hover:bg-accent hover:text-accent-foreground': variant === 'ghost',
            'bg-destructive text-destructive-foreground hover:bg-destructive/90': variant === 'destructive',
          },
          {
            'h-10 px-4 py-2': size === 'default',
            'h-9 px-3': size === 'sm',
            'h-11 px-8': size === 'lg',
          },
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'
```

#### card.tsx
```typescript
import * as React from 'react'
import { cn } from '../lib/utils'

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)}
      {...props}
    />
  )
)
Card.displayName = 'Card'

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
  )
)
CardHeader.displayName = 'CardHeader'

export const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn('text-2xl font-semibold leading-none tracking-tight', className)} {...props} />
  )
)
CardTitle.displayName = 'CardTitle'

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  )
)
CardContent.displayName = 'CardContent'
```

#### loading.tsx
```typescript
import * as React from 'react'
import { cn } from '../lib/utils'

export interface LoadingProps {
  className?: string
  size?: 'sm' | 'default' | 'lg'
}

export const Loading: React.FC<LoadingProps> = ({ className, size = 'default' }) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    default: 'h-8 w-8',
    lg: 'h-12 w-12',
  }

  return (
    <div className={cn('flex items-center justify-center', className)}>
      <div
        className={cn(
          'animate-spin rounded-full border-2 border-current border-t-transparent',
          sizeClasses[size]
        )}
      />
    </div>
  )
}
```

#### table.tsx
```typescript
import * as React from 'react'
import { cn } from '../lib/utils'

export const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <div className="relative w-full overflow-auto">
      <table ref={ref} className={cn('w-full caption-bottom text-sm', className)} {...props} />
    </div>
  )
)
Table.displayName = 'Table'

export const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => (
    <thead ref={ref} className={cn('[&_tr]:border-b', className)} {...props} />
  )
)
TableHeader.displayName = 'TableHeader'

export const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => (
    <tbody ref={ref} className={cn('[&_tr:last-child]:border-0', className)} {...props} />
  )
)
TableBody.displayName = 'TableBody'

export const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(
  ({ className, ...props }, ref) => (
    <tr ref={ref} className={cn('border-b transition-colors hover:bg-muted/50', className)} {...props} />
  )
)
TableRow.displayName = 'TableRow'

export const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <th
      ref={ref}
      className={cn('h-12 px-4 text-left align-middle font-medium text-muted-foreground', className)}
      {...props}
    />
  )
)
TableHead.displayName = 'TableHead'

export const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <td ref={ref} className={cn('p-4 align-middle', className)} {...props} />
  )
)
TableCell.displayName = 'TableCell'
```

### 4. 建立 utils

```typescript
// /home/user/Sales_ai_automation_v3/packages/ui/src/lib/utils.ts
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

### 5. 建立 index.ts

```typescript
// /home/user/Sales_ai_automation_v3/packages/ui/src/index.ts
export * from './button'
export * from './card'
export * from './loading'
export * from './table'
export * from './lib/utils'
// 導出其他元件...
```

### 6. 建立完成報告

建立 `/home/user/Sales_ai_automation_v3/packages/ui/AGENT_B_COMPLETE.md`：

```markdown
# Agent B 完成報告

## 遷移的元件

| 元件 | 來源 | 修改 |
|------|------|------|
| Button | 舊專案 | 調整 import |
| Card | 舊專案 | 調整 import |
| ... | ... | ... |

## 新增的元件

| 元件 | 說明 |
|------|------|
| Loading | 載入指示器 |
| ... | ... |

## 使用範例

```tsx
import { Button, Card, CardContent, Loading } from '@sales-ai/ui'

function Example() {
  return (
    <Card>
      <CardContent>
        <Button>Click me</Button>
        <Loading />
      </CardContent>
    </Card>
  )
}
```

## 注意事項

（記錄任何問題或特殊處理）
```

## 完成標準

- [ ] 所有核心元件建立
- [ ] utils.ts 建立
- [ ] index.ts 正確導出
- [ ] 元件可正常 import
- [ ] 完成報告建立
