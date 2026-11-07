"""Explicit fake model behavior for offline demos; all evidence comes from real tools."""

import json
from typing import Literal

from querypilot.agent.provider import ProviderTurn


class MockProvider:
    mode: Literal["mock"] = "mock"

    async def respond(
        self, instructions: str, history: list[dict], tools: list[dict], *, final: bool = False
    ) -> ProviderTurn:
        if not final:
            question = history[0]["content"]
            lower = question.casefold()
            if "failed" in lower and "payment" in lower:
                name, values = "get_payment_status_summary", {}
            elif "product" in lower and ("top" in lower or "revenue" in lower):
                name, values = "get_top_products", {"limit": 5}
            elif "revenue" in lower:
                name, values = "get_revenue_summary", {"group_by": "month"}
            elif "customer" in lower and "order" in lower:
                name, values = "get_customer_order_summary", {"limit": 5}
            else:
                name, values = "search_business_documents", {"query": question, "top_k": 3}
            schema = next(tool["parameters"] for tool in tools if tool["name"] == name)
            arguments = {field: values.get(field) for field in schema["properties"]}
            return ProviderTurn(
                [
                    {
                        "type": "function_call",
                        "id": "fc_mock_1",
                        "call_id": "mock_call_1",
                        "name": name,
                        "arguments": json.dumps(arguments),
                        "status": "completed",
                    }
                ]
            )
        answers = []
        for item in history:
            if item.get("type") != "function_call_output":
                continue
            payload = json.loads(item["output"])
            result = payload["result"]
            if result["status"] != "success":
                continue
            data = result["data"]
            evidence = payload["evidence_id"]
            if data["operation"] == "search_business_documents" and data["matches"]:
                hit = data["matches"][0]
                answers.append(f"{hit['excerpt']} [{evidence}] [{hit['source_citation']}]")
            elif data.get("rows"):
                row = data["rows"][0]
                if data["operation"] == "get_top_products":
                    answers.extend(
                        f"{product['name']}: USD {product['revenue']} [{evidence}]."
                        for product in data["rows"]
                    )
                elif data["operation"] == "get_payment_status_summary":
                    row = next((r for r in data["rows"] if r["payment_status"] == "failed"), row)
                    answers.append(
                        f"{row['payment_count']} {row['payment_status']} "
                        f"payment attempts [{evidence}]."
                    )
                elif data["operation"] == "get_revenue_summary":
                    answers.extend(
                        f"{bucket['bucket']}: USD {bucket['revenue']} [{evidence}]."
                        for bucket in data["rows"]
                    )
                    if data.get("truncated"):
                        answers.append(
                            "Only forwarded revenue buckets are shown; results are incomplete."
                        )
                else:
                    answers.append(
                        f"Customer {row['customer_id']}: {row['order_count']} orders [{evidence}]."
                    )
        return ProviderTurn([], "\n".join(answers))

    async def close(self) -> None:
        pass


class MultiStepMockProvider(MockProvider):
    """Deterministic offline fixture; never used for live dispatch."""

    async def respond(self, instructions, history, tools, *, final=False) -> ProviderTurn:
        if final:
            return await super().respond(instructions, history, tools, final=True)
        lower = history[0]["content"].casefold()
        plan = []
        if "product" in lower and ("top" in lower or "revenue" in lower):
            plan.append(("get_top_products", {"limit": 5}))
        elif "revenue" in lower:
            plan.append(("get_revenue_summary", {"group_by": "month"}))
        elif (
            "failed" in lower
            and "payment" in lower
            and (
                "handled" not in lower
                or any(term in lower for term in ("how many", "count", "number of"))
            )
        ):
            plan.append(("get_payment_status_summary", {}))
        elif "customer" in lower and "order" in lower:
            plan.append(("get_customer_order_summary", {"limit": 5}))
        if "policy" in lower or "return" in lower or "handled" in lower or not plan:
            query = (
                "failed payments and retries"
                if "failed" in lower and "payment" in lower
                else "product return window"
                if "return" in lower or "refund" in lower
                else history[0]["content"]
            )
            plan.append(("search_business_documents", {"query": query, "top_k": 1}))
        completed = sum(item.get("type") == "function_call_output" for item in history)
        if completed >= len(plan):
            return await super().respond(instructions, history, tools, final=True)
        name, values = plan[completed]
        schema = next(tool["parameters"] for tool in tools if tool["name"] == name)
        return ProviderTurn(
            [
                {
                    "type": "function_call",
                    "id": f"fc_mock_{completed + 1}",
                    "call_id": f"mock_call_{completed + 1}",
                    "name": name,
                    "arguments": json.dumps(
                        {field: values.get(field) for field in schema["properties"]}
                    ),
                    "status": "completed",
                }
            ]
        )
