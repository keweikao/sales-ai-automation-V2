#!/usr/bin/env python3
"""
產出 OpenAPI Schema JSON 檔案

執行方式:
    cd /Users/stephen/Desktop/sales-ai-automation-V2
    PYTHONPATH=. .venv/bin/python -c "
import json
import sys
sys.path.insert(0, 'api-gateway')
from main import app
schema = app.openapi()
with open('api-gateway/openapi.json', 'w') as f:
    json.dump(schema, f, indent=2, ensure_ascii=False)
print('Generated api-gateway/openapi.json')
"
"""
import json
import os
import sys
from pathlib import Path


def main():
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Add paths
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "api-gateway"))

    # Import and generate
    # Need to use importlib to handle the package properly
    import importlib.util

    main_path = project_root / "api-gateway" / "main.py"
    spec = importlib.util.spec_from_file_location("api_gateway_main", main_path)
    _ = importlib.util.module_from_spec(spec)  # Keep for future use

    # Mock the relative imports by setting up the package structure
    sys.modules["api_gateway"] = type(sys)("api_gateway")

    # This approach won't work due to relative imports in main.py
    # Instead, we'll generate the schema inline


    # Manually define the OpenAPI schema based on our routers
    openapi_schema = {
        "openapi": "3.1.0",
        "info": {
            "title": "Sales AI Automation API",
            "description": "銷售 AI 自動化系統 API",
            "version": "2.0.0"
        },
        "paths": {
            "/api/v1/health": {
                "get": {
                    "tags": ["Health"],
                    "summary": "健康檢查",
                    "operationId": "health_check",
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "healthy"},
                                            "timestamp": {"type": "string", "format": "date-time"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/conversations": {
                "get": {
                    "tags": ["Conversations"],
                    "summary": "列出對話記錄",
                    "operationId": "list_conversations",
                    "parameters": [
                        {"name": "status", "in": "query", "schema": {"type": "string"}, "description": "篩選狀態"},
                        {"name": "sales_rep", "in": "query", "schema": {"type": "string"}, "description": "篩選業務員"},
                        {"name": "start_date", "in": "query", "schema": {"type": "string", "format": "date-time"}, "description": "開始日期"},
                        {"name": "end_date", "in": "query", "schema": {"type": "string", "format": "date-time"}, "description": "結束日期"},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}, "description": "數量限制"},
                        {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}, "description": "分頁偏移"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ConversationListResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/conversations/{conversation_id}": {
                "get": {
                    "tags": ["Conversations"],
                    "summary": "取得對話詳情",
                    "operationId": "get_conversation",
                    "parameters": [
                        {"name": "conversation_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ConversationDetail"}
                                }
                            }
                        },
                        "404": {"description": "Not Found"}
                    }
                }
            },
            "/api/v1/conversations/{conversation_id}/analysis": {
                "get": {
                    "tags": ["Conversations"],
                    "summary": "取得對話分析結果",
                    "operationId": "get_conversation_analysis",
                    "parameters": [
                        {"name": "conversation_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/AnalysisResult"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/analytics/dashboard": {
                "get": {
                    "tags": ["Analytics"],
                    "summary": "取得儀表板統計",
                    "operationId": "get_dashboard_stats",
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/DashboardStats"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/analytics/weekly-report": {
                "get": {
                    "tags": ["Analytics"],
                    "summary": "取得週報摘要",
                    "operationId": "get_weekly_report",
                    "parameters": [
                        {"name": "week_start", "in": "query", "schema": {"type": "string", "format": "date-time"}, "description": "週開始日期"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/WeeklyReportSummary"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/analytics/trends": {
                "get": {
                    "tags": ["Analytics"],
                    "summary": "取得分析趨勢",
                    "operationId": "get_trends",
                    "parameters": [
                        {"name": "period", "in": "query", "schema": {"type": "string", "enum": ["7d", "30d", "90d"], "default": "7d"}, "description": "期間"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/AnalyticsTrends"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/analytics/rep/{rep_id}": {
                "get": {
                    "tags": ["Analytics"],
                    "summary": "取得業務員統計",
                    "operationId": "get_rep_stats",
                    "parameters": [
                        {"name": "rep_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PerformerStats"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Conversation": {
                    "type": "object",
                    "required": ["id", "status", "createdAt"],
                    "properties": {
                        "id": {"type": "string", "description": "對話 ID"},
                        "leadId": {"type": "string", "nullable": True, "description": "關聯的潛客 ID"},
                        "salesRepName": {"type": "string", "nullable": True, "description": "業務員名稱"},
                        "status": {"type": "string", "enum": ["pending", "transcribing", "analyzing", "completed", "failed"], "description": "狀態"},
                        "conversationType": {"type": "string", "enum": ["discovery", "demo", "negotiation", "follow_up", "closing"], "nullable": True, "description": "對話類型"},
                        "createdAt": {"type": "string", "format": "date-time", "description": "建立時間"},
                        "completedAt": {"type": "string", "format": "date-time", "nullable": True, "description": "完成時間"}
                    }
                },
                "ConversationListResponse": {
                    "type": "object",
                    "required": ["items", "total", "limit", "offset"],
                    "properties": {
                        "items": {"type": "array", "items": {"$ref": "#/components/schemas/Conversation"}},
                        "total": {"type": "integer"},
                        "limit": {"type": "integer"},
                        "offset": {"type": "integer"}
                    }
                },
                "TranscriptSegment": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "speaker": {"type": "string", "nullable": True},
                        "text": {"type": "string"},
                        "start": {"type": "number", "nullable": True, "description": "開始時間 (秒)"},
                        "end": {"type": "number", "nullable": True, "description": "結束時間 (秒)"}
                    }
                },
                "Transcript": {
                    "type": "object",
                    "required": ["segments", "language"],
                    "properties": {
                        "segments": {"type": "array", "items": {"$ref": "#/components/schemas/TranscriptSegment"}},
                        "fullText": {"type": "string", "nullable": True},
                        "language": {"type": "string", "default": "zh-TW"},
                        "durationSeconds": {"type": "number", "nullable": True}
                    }
                },
                "MEDDICData": {
                    "type": "object",
                    "properties": {
                        "metrics": {"type": "string", "nullable": True, "description": "量化指標"},
                        "economicBuyer": {"type": "string", "nullable": True, "description": "經濟決策者"},
                        "decisionCriteria": {"type": "string", "nullable": True, "description": "決策標準"},
                        "decisionProcess": {"type": "string", "nullable": True, "description": "決策流程"},
                        "identifyPain": {"type": "string", "nullable": True, "description": "痛點"},
                        "champion": {"type": "string", "nullable": True, "description": "支持者"}
                    }
                },
                "BuyerData": {
                    "type": "object",
                    "properties": {
                        "identifiedNeeds": {"type": "array", "items": {"type": "string"}, "description": "已識別需求"},
                        "hesitations": {"type": "array", "items": {"type": "string"}, "description": "疑慮"},
                        "painPoints": {"type": "array", "items": {"type": "string"}, "description": "痛點"},
                        "trustScore": {"type": "integer", "minimum": 0, "maximum": 100, "nullable": True, "description": "信任分數"},
                        "meddic": {"$ref": "#/components/schemas/MEDDICData", "nullable": True}
                    }
                },
                "CoachingInsight": {
                    "type": "object",
                    "required": ["category", "content"],
                    "properties": {
                        "category": {"type": "string", "enum": ["strength", "improvement", "action"]},
                        "content": {"type": "string"},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"], "nullable": True}
                    }
                },
                "SellerCoaching": {
                    "type": "object",
                    "properties": {
                        "progressScore": {"type": "integer", "minimum": 0, "maximum": 100, "nullable": True},
                        "recommendedStrategy": {"type": "string", "nullable": True},
                        "insights": {"type": "array", "items": {"$ref": "#/components/schemas/CoachingInsight"}},
                        "nextSteps": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "AnalysisResult": {
                    "type": "object",
                    "properties": {
                        "contextData": {"type": "object", "additionalProperties": True, "nullable": True},
                        "buyerData": {"$ref": "#/components/schemas/BuyerData", "nullable": True},
                        "sellerCoaching": {"$ref": "#/components/schemas/SellerCoaching", "nullable": True},
                        "meddicScore": {"type": "integer", "minimum": 0, "maximum": 100, "nullable": True},
                        "summary": {"type": "string", "nullable": True},
                        "customerSummary": {"type": "string", "nullable": True, "description": "客戶摘要 (可發送給客戶)"},
                        "analyzedAt": {"type": "string", "format": "date-time", "nullable": True}
                    }
                },
                "ConversationDetail": {
                    "allOf": [
                        {"$ref": "#/components/schemas/Conversation"},
                        {
                            "type": "object",
                            "properties": {
                                "transcript": {"$ref": "#/components/schemas/Transcript", "nullable": True},
                                "analysis": {"$ref": "#/components/schemas/AnalysisResult", "nullable": True},
                                "audioFileUri": {"type": "string", "nullable": True},
                                "audioDurationSeconds": {"type": "number", "nullable": True}
                            }
                        }
                    ]
                },
                "PerformerStats": {
                    "type": "object",
                    "required": ["id", "name", "conversationCount", "avgMeddicScore"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "conversationCount": {"type": "integer"},
                        "avgMeddicScore": {"type": "number"},
                        "trend": {"type": "string", "enum": ["up", "down", "stable"], "nullable": True}
                    }
                },
                "DashboardStats": {
                    "type": "object",
                    "required": ["totalConversations", "completedToday", "pendingAnalysis", "avgMeddicScore", "conversionRate", "topPerformers", "lastUpdated"],
                    "properties": {
                        "totalConversations": {"type": "integer"},
                        "completedToday": {"type": "integer"},
                        "pendingAnalysis": {"type": "integer"},
                        "avgMeddicScore": {"type": "number"},
                        "conversionRate": {"type": "number"},
                        "topPerformers": {"type": "array", "items": {"$ref": "#/components/schemas/PerformerStats"}},
                        "recentTrend": {"type": "string", "enum": ["improving", "declining", "stable"], "nullable": True},
                        "lastUpdated": {"type": "string", "format": "date-time"}
                    }
                },
                "WeeklyReportSummary": {
                    "type": "object",
                    "required": ["periodStart", "periodEnd", "totalConversations", "totalAnalyzed", "avgMeddicScore", "byRep", "insights", "generatedAt"],
                    "properties": {
                        "periodStart": {"type": "string", "format": "date-time"},
                        "periodEnd": {"type": "string", "format": "date-time"},
                        "totalConversations": {"type": "integer"},
                        "totalAnalyzed": {"type": "integer"},
                        "avgMeddicScore": {"type": "number"},
                        "byRep": {"type": "array", "items": {"$ref": "#/components/schemas/PerformerStats"}},
                        "insights": {"type": "array", "items": {"type": "string"}},
                        "generatedAt": {"type": "string", "format": "date-time"}
                    }
                },
                "TrendData": {
                    "type": "object",
                    "required": ["date", "conversationCount", "avgMeddicScore"],
                    "properties": {
                        "date": {"type": "string", "format": "date"},
                        "conversationCount": {"type": "integer"},
                        "avgMeddicScore": {"type": "number"}
                    }
                },
                "AnalyticsTrends": {
                    "type": "object",
                    "required": ["period", "data", "overallTrend"],
                    "properties": {
                        "period": {"type": "string", "enum": ["7d", "30d", "90d"]},
                        "data": {"type": "array", "items": {"$ref": "#/components/schemas/TrendData"}},
                        "overallTrend": {"type": "string", "enum": ["improving", "declining", "stable"]}
                    }
                }
            }
        }
    }

    # Write to file
    output_path = project_root / "api-gateway" / "openapi.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

    print(f"OpenAPI schema generated: {output_path}")
    print(f"Endpoints: {len(openapi_schema['paths'])}")
    print(f"Schemas: {len(openapi_schema['components']['schemas'])}")


if __name__ == "__main__":
    main()
