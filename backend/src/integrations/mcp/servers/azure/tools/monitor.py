"""Azure Monitor Tools.

Provides MCP tools for metrics, alerts, and log operations.

Tools:
    - get_metrics: Get resource metrics
    - list_alerts: List active alerts
    - get_metric_definitions: Get available metrics for a resource
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from ....core.types import (
    ToolSchema,
    ToolParameter,
    ToolInputType,
    ToolResult,
)
from ..client import AzureClientManager

logger = logging.getLogger(__name__)


class MonitorTools:
    """Monitor tools for Azure MCP Server.

    Provides monitoring and alerting capabilities.

    Permission Levels:
        - Level 1 (READ): All tools (read-only operations)

    Example:
        >>> manager = AzureClientManager(config)
        >>> tools = MonitorTools(manager)
        >>> result = await tools.get_metrics(resource_id, ["Percentage CPU"])
        >>> print(result.content)
    """

    # Permission levels for tools
    PERMISSION_LEVELS = {
        "get_metrics": 1,
        "list_alerts": 1,
        "get_metric_definitions": 1,
    }

    def __init__(self, client_manager: AzureClientManager):
        """Initialize Monitor tools.

        Args:
            client_manager: Azure client manager instance
        """
        self._manager = client_manager

    @staticmethod
    def get_schemas() -> List[ToolSchema]:
        """Get all Monitor tool schemas.

        Returns:
            List of ToolSchema definitions for MCP protocol
        """
        return [
            ToolSchema(
                name="get_metrics",
                description="Get monitoring metrics for a resource",
                parameters=[
                    ToolParameter(
                        name="resource_id",
                        type=ToolInputType.STRING,
                        description="Azure resource ID",
                        required=True,
                    ),
                    ToolParameter(
                        name="metric_names",
                        type=ToolInputType.ARRAY,
                        description="List of metric names to retrieve (e.g., ['Percentage CPU', 'Network In'])",
                        required=True,
                    ),
                    ToolParameter(
                        name="timespan",
                        type=ToolInputType.STRING,
                        description="Time range in ISO 8601 duration format (e.g., PT1H for 1 hour, P1D for 1 day)",
                        required=False,
                    ),
                    ToolParameter(
                        name="interval",
                        type=ToolInputType.STRING,
                        description="Aggregation interval (e.g., PT1M, PT5M, PT1H)",
                        required=False,
                    ),
                    ToolParameter(
                        name="aggregation",
                        type=ToolInputType.STRING,
                        description="Aggregation type (Average, Minimum, Maximum, Total, Count)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="list_alerts",
                description="List active alerts in the subscription",
                parameters=[
                    ToolParameter(
                        name="resource_group",
                        type=ToolInputType.STRING,
                        description="Optional resource group filter",
                        required=False,
                    ),
                    ToolParameter(
                        name="severity",
                        type=ToolInputType.STRING,
                        description="Alert severity filter (Sev0, Sev1, Sev2, Sev3, Sev4)",
                        required=False,
                    ),
                    ToolParameter(
                        name="alert_state",
                        type=ToolInputType.STRING,
                        description="Alert state filter (New, Acknowledged, Closed)",
                        required=False,
                    ),
                ],
            ),
            ToolSchema(
                name="get_metric_definitions",
                description="Get available metric definitions for a resource",
                parameters=[
                    ToolParameter(
                        name="resource_id",
                        type=ToolInputType.STRING,
                        description="Azure resource ID",
                        required=True,
                    ),
                ],
            ),
        ]

    async def get_metrics(
        self,
        resource_id: str,
        metric_names: List[str],
        timespan: str = "PT1H",
        interval: str = "PT5M",
        aggregation: str = "Average",
    ) -> ToolResult:
        """Get resource metrics.

        Args:
            resource_id: Azure resource ID
            metric_names: List of metric names
            timespan: Time range (ISO 8601 duration)
            interval: Aggregation interval
            aggregation: Aggregation type

        Returns:
            ToolResult with metric data
        """
        try:
            monitor = self._manager.monitor

            # Calculate time range
            end_time = datetime.utcnow()
            # Parse timespan (simplified parsing)
            hours = 1
            if timespan.startswith("PT"):
                if "H" in timespan:
                    hours = int(timespan.replace("PT", "").replace("H", ""))
                elif "M" in timespan:
                    hours = int(timespan.replace("PT", "").replace("M", "")) / 60
            elif timespan.startswith("P"):
                if "D" in timespan:
                    hours = int(timespan.replace("P", "").replace("D", "")) * 24

            start_time = end_time - timedelta(hours=hours)
            timespan_str = f"{start_time.isoformat()}Z/{end_time.isoformat()}Z"

            # Get metrics
            metrics_data = monitor.metrics.list(
                resource_id,
                timespan=timespan_str,
                interval=interval,
                metricnames=",".join(metric_names),
                aggregation=aggregation,
            )

            result_metrics = []
            for metric in metrics_data.value:
                metric_info = {
                    "name": metric.name.value if metric.name else "Unknown",
                    "unit": str(metric.unit) if metric.unit else "Unknown",
                    "timeseries": [],
                }

                for ts in metric.timeseries or []:
                    series_data = {
                        "metadata": [],
                        "data": [],
                    }

                    # Get metadata
                    if ts.metadatavalues:
                        for md in ts.metadatavalues:
                            series_data["metadata"].append({
                                "name": md.name.value if md.name else None,
                                "value": md.value,
                            })

                    # Get data points
                    for dp in ts.data or []:
                        data_point = {
                            "timestamp": dp.time_stamp.isoformat() if dp.time_stamp else None,
                        }
                        # Add aggregation values
                        if aggregation.lower() == "average" and dp.average is not None:
                            data_point["value"] = dp.average
                        elif aggregation.lower() == "minimum" and dp.minimum is not None:
                            data_point["value"] = dp.minimum
                        elif aggregation.lower() == "maximum" and dp.maximum is not None:
                            data_point["value"] = dp.maximum
                        elif aggregation.lower() == "total" and dp.total is not None:
                            data_point["value"] = dp.total
                        elif aggregation.lower() == "count" and dp.count is not None:
                            data_point["value"] = dp.count
                        else:
                            # Include all available values
                            data_point["average"] = dp.average
                            data_point["minimum"] = dp.minimum
                            data_point["maximum"] = dp.maximum
                            data_point["total"] = dp.total
                            data_point["count"] = dp.count

                        series_data["data"].append(data_point)

                    metric_info["timeseries"].append(series_data)

                result_metrics.append(metric_info)

            logger.info(f"Retrieved {len(result_metrics)} metrics for resource")
            return ToolResult(
                success=True,
                content={
                    "resource_id": resource_id,
                    "timespan": timespan,
                    "interval": interval,
                    "aggregation": aggregation,
                    "metrics": result_metrics,
                },
            )

        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def list_alerts(
        self,
        resource_group: Optional[str] = None,
        severity: Optional[str] = None,
        alert_state: Optional[str] = None,
    ) -> ToolResult:
        """List active alerts.

        Args:
            resource_group: Optional resource group filter
            severity: Alert severity filter
            alert_state: Alert state filter

        Returns:
            ToolResult with list of alerts
        """
        try:
            monitor = self._manager.monitor

            # Build filter parameters
            # Note: Alert APIs vary by Azure Monitor version
            # This implementation uses a simplified approach

            alerts_list = []

            # Try to list metric alerts
            try:
                if resource_group:
                    metric_alerts = monitor.metric_alerts.list_by_resource_group(resource_group)
                else:
                    metric_alerts = monitor.metric_alerts.list_by_subscription()

                for alert in metric_alerts:
                    # Apply filters
                    if severity and str(alert.severity) != severity:
                        continue

                    alerts_list.append({
                        "name": alert.name,
                        "type": "metric_alert",
                        "severity": str(alert.severity) if alert.severity else None,
                        "enabled": alert.enabled,
                        "description": alert.description,
                        "scopes": alert.scopes or [],
                        "id": alert.id,
                        "location": alert.location,
                    })
            except Exception as e:
                logger.warning(f"Could not list metric alerts: {e}")

            # Try to list activity log alerts
            try:
                if resource_group:
                    activity_alerts = monitor.activity_log_alerts.list_by_resource_group(
                        resource_group
                    )
                else:
                    activity_alerts = monitor.activity_log_alerts.list_by_subscription_id()

                for alert in activity_alerts:
                    alerts_list.append({
                        "name": alert.name,
                        "type": "activity_log_alert",
                        "enabled": alert.enabled,
                        "description": alert.description,
                        "scopes": alert.scopes or [],
                        "id": alert.id,
                        "location": alert.location,
                    })
            except Exception as e:
                logger.warning(f"Could not list activity log alerts: {e}")

            logger.info(f"Found {len(alerts_list)} alerts")
            return ToolResult(
                success=True,
                content=alerts_list,
                metadata={"count": len(alerts_list)},
            )

        except Exception as e:
            logger.error(f"Failed to list alerts: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )

    async def get_metric_definitions(
        self,
        resource_id: str,
    ) -> ToolResult:
        """Get available metric definitions for a resource.

        Args:
            resource_id: Azure resource ID

        Returns:
            ToolResult with metric definitions
        """
        try:
            monitor = self._manager.monitor

            definitions = monitor.metric_definitions.list(resource_id)

            metric_defs = []
            for md in definitions:
                metric_def = {
                    "name": md.name.value if md.name else "Unknown",
                    "display_name": md.name.localized_value if md.name else None,
                    "unit": str(md.unit) if md.unit else "Unknown",
                    "primary_aggregation_type": str(md.primary_aggregation_type) if md.primary_aggregation_type else None,
                    "supported_aggregation_types": [
                        str(a) for a in (md.supported_aggregation_types or [])
                    ],
                    "metric_availabilities": [],
                    "dimensions": [],
                }

                # Add metric availabilities
                for ma in md.metric_availabilities or []:
                    metric_def["metric_availabilities"].append({
                        "time_grain": str(ma.time_grain) if ma.time_grain else None,
                        "retention": str(ma.retention) if ma.retention else None,
                    })

                # Add dimensions
                for dim in md.dimensions or []:
                    metric_def["dimensions"].append({
                        "name": dim.value if hasattr(dim, "value") else str(dim),
                        "display_name": dim.localized_value if hasattr(dim, "localized_value") else None,
                    })

                metric_defs.append(metric_def)

            logger.info(f"Found {len(metric_defs)} metric definitions")
            return ToolResult(
                success=True,
                content={
                    "resource_id": resource_id,
                    "metric_definitions": metric_defs,
                },
                metadata={"count": len(metric_defs)},
            )

        except Exception as e:
            logger.error(f"Failed to get metric definitions: {e}")
            return ToolResult(
                success=False,
                content=None,
                error=str(e),
            )
