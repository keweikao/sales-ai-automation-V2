"""
CLI 工具 - 提供命令列介面使用程式碼智能功能
"""

import click
import json
from pathlib import Path

from repo_analyzer import SalesAIRepoAnalyzer
from symbol_indexer import SmartCodeSearch


@click.group()
def cli():
    """Sales AI Automation 程式碼智能工具"""
    pass


@cli.command()
@click.option('--output', '-o', help='輸出檔案路徑（JSON 格式）')
def analyze_deps(output):
    """分析服務依賴關係"""
    click.echo("🔍 分析服務依賴關係...")
    
    analyzer = SalesAIRepoAnalyzer()
    result = analyzer.analyze_service_dependencies()
    
    if result["status"] == "success":
        click.echo("✓ 分析完成")
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            click.echo(f"✓ 結果已儲存至: {output}")
        else:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(f"✗ 分析失敗: {result.get('error')}", err=True)


@cli.command()
def find_agents():
    """找出所有 AI 代理實作"""
    click.echo("🔍 搜尋 AI 代理...")
    
    analyzer = SalesAIRepoAnalyzer()
    agents = analyzer.find_agent_implementations()
    
    if agents:
        click.echo(f"\n找到 {len(agents)} 個代理:\n")
        for agent in agents:
            click.echo(f"  📍 {agent['file']}:{agent['line']}")
            click.echo(f"     {agent['content']}\n")
    else:
        click.echo("未找到代理實作")


@cli.command()
@click.argument('query')
@click.option('--limit', '-l', default=10, help='結果數量限制')
def search(query, limit):
    """搜尋程式碼符號"""
    click.echo(f"🔍 搜尋: {query}")
    
    searcher = SmartCodeSearch()
    results = searcher.search(query, limit=limit)
    
    if results:
        click.echo(f"\n找到 {len(results)} 個結果:\n")
        for r in results:
            click.echo(f"  📍 {r['name']} ({r['type']})")
            click.echo(f"     {r['file']}:{r['line_start']}-{r['line_end']}\n")
    else:
        click.echo("未找到符合的結果")


@cli.command()
@click.option('--force', '-f', is_flag=True, help='強制重建索引')
def build_index(force):
    """建立符號索引"""
    click.echo("🔨 建立符號索引...")
    
    searcher = SmartCodeSearch()
    result = searcher.build_index(force_rebuild=force)
    
    if result["status"] == "success":
        click.echo(f"✓ 索引建立完成")
        click.echo(f"  總符號數: {result['total_symbols']}")
        click.echo(f"  索引檔案: {result['index_file']}")
    elif result["status"] == "skipped":
        click.echo(f"⊘ {result['message']}")
    else:
        click.echo(f"✗ 建立失敗: {result.get('error')}", err=True)


@cli.command()
def index_stats():
    """顯示索引統計資訊"""
    click.echo("📊 索引統計資訊:\n")
    
    searcher = SmartCodeSearch()
    stats = searcher.get_stats()
    
    if stats["status"] == "success":
        click.echo(f"總符號數: {stats['total_symbols']}")
        click.echo(f"\n類型分布:")
        for symbol_type, count in stats['type_distribution'].items():
            click.echo(f"  {symbol_type}: {count}")
        click.echo(f"\n索引檔案: {stats['index_file']}")
    elif stats["status"] == "no_index":
        click.echo(f"⊘ {stats['message']}")
        click.echo("請先執行: python cli.py build-index")
    else:
        click.echo(f"✗ 錯誤: {stats.get('error')}", err=True)


@cli.command()
def extract_endpoints():
    """提取所有 API 端點"""
    click.echo("🔍 提取 API 端點...")
    
    analyzer = SalesAIRepoAnalyzer()
    endpoints = analyzer.extract_api_endpoints()
    
    if endpoints:
        click.echo(f"\n找到 {len(endpoints)} 個端點:\n")
        for ep in endpoints:
            click.echo(f"  📍 {ep['file']}:{ep['line']}")
            click.echo(f"     {ep['content']}\n")
    else:
        click.echo("未找到 API 端點")


if __name__ == '__main__':
    cli()
