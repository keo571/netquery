"""
Result interpretation prompt templates.
"""
from typing import Dict, Any, List
import json


# Common response guidelines
_RESPONSE_GUIDELINES = """
Guidelines:
- Keep explanations technical and actionable
- Make responses conversational and helpful
- Focus on network infrastructure context (operational health, performance, capacity)
- Provide direct answers first, then supporting details
"""

ERROR_ANALYSIS_PROMPT = """Analyze the following SQL execution error and provide user-friendly guidance.

Original Query: {original_query}
Generated SQL: {sql_query}
Error: {error_message}

Provide:
1. Simple explanation of what went wrong
2. Possible causes of the error
3. Suggestions for fixing the issue
4. Alternative approaches to get the desired data
""" + _RESPONSE_GUIDELINES

RESPONSE_FORMAT_TEMPLATE = """Format a comprehensive response for the user's query.

Original Query: {original_query}
Results: {results}
Execution Time: {execution_time}ms
Row Count: {row_count}

Include:
1. Direct answer to the user's question
2. Well-formatted data presentation
3. Key insights from the results
4. Brief explanation of how the answer was found
""" + _RESPONSE_GUIDELINES


def create_result_interpretation_prompt(
    query: str,
    results: List[Dict],
    sql_query: str = None
) -> str:
    """Create a prompt for interpreting and explaining query results."""
    
    total_count = len(results)
    
    # Generate intelligent statistical insights
    stats_summary = _generate_statistical_summary(results)
    patterns = _identify_patterns(results)
    
    return f"""Your task is to provide intelligent analysis of database query results for a network engineer.

**Original Question:** "{query}"

**Dataset:** {total_count} total rows

**Statistical Summary:**
{stats_summary}

**Key Patterns Identified:**
{patterns}

**Instructions:**
1. **Direct Answer:** Start with a clear answer to the original question
2. **Statistical Insights:** Use the statistical summary to provide percentage breakdowns and distributions
3. **Operational Impact:** Explain what these patterns mean for network operations, capacity planning, and troubleshooting
4. **Actionable Recommendations:** Suggest specific actions based on the data (e.g., investigate unhealthy resources, review duplicate IPs)
5. **Risk Assessment:** Highlight any potential issues or anomalies that need attention
6. **Keep Professional:** Write for a network engineer who needs actionable intelligence

{_RESPONSE_GUIDELINES.strip()}"""


def _generate_statistical_summary(results: List[Dict]) -> str:
    """Generate statistical insights from the complete dataset."""
    if not results:
        return "No data to analyze."
    
    summary_parts = []
    
    # Analyze categorical fields
    categorical_fields = ['status', 'datacenter', 'lb_type', 'algorithm']
    
    for field in categorical_fields:
        if field in results[0]:
            values = [row.get(field) for row in results if row.get(field)]
            if values:
                value_counts = {}
                for value in values:
                    value_counts[value] = value_counts.get(value, 0) + 1
                
                # Sort by count descending
                sorted_counts = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
                total = len(values)
                
                field_summary = f"**{field.upper()}:**\n"
                for value, count in sorted_counts:
                    percentage = (count / total) * 100
                    field_summary += f"- {value}: {count} ({percentage:.1f}%)\n"
                
                summary_parts.append(field_summary)
    
    # Analyze duplicates (common network issue)
    ip_fields = ['vip_address', 'ip_address']
    for field in ip_fields:
        if field in results[0]:
            ips = [row.get(field) for row in results if row.get(field)]
            ip_counts = {}
            for ip in ips:
                ip_counts[ip] = ip_counts.get(ip, 0) + 1
            
            duplicates = {ip: count for ip, count in ip_counts.items() if count > 1}
            if duplicates:
                dup_summary = f"**DUPLICATE {field.upper()}S (Potential Issues):**\n"
                for ip, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True):
                    dup_summary += f"- {ip}: used by {count} resources\n"
                summary_parts.append(dup_summary)
    
    return "\n".join(summary_parts) if summary_parts else "No significant patterns found."


def _identify_patterns(results: List[Dict]) -> str:
    """Identify operational patterns and anomalies."""
    if not results:
        return "No patterns to analyze."
    
    patterns = []
    
    # Health status analysis
    if 'status' in results[0]:
        statuses = [row.get('status') for row in results if row.get('status')]
        total = len(statuses)
        unhealthy_states = ['unhealthy', 'down', 'failed', 'error', 'maintenance', 'draining']
        unhealthy_count = sum(1 for status in statuses if status and status.lower() in unhealthy_states)
        
        if unhealthy_count > 0:
            unhealthy_pct = (unhealthy_count / total) * 100
            if unhealthy_pct > 25:
                patterns.append(f"🚨 HIGH ALERT: {unhealthy_pct:.1f}% of resources are in non-optimal states")
            elif unhealthy_pct > 10:
                patterns.append(f"⚠️  MODERATE CONCERN: {unhealthy_pct:.1f}% of resources need attention")
            else:
                patterns.append(f"✓ ACCEPTABLE: Only {unhealthy_pct:.1f}% of resources in non-optimal states")
    
    # Geographic distribution
    if 'datacenter' in results[0]:
        datacenters = [row.get('datacenter') for row in results if row.get('datacenter')]
        dc_counts = {}
        for dc in datacenters:
            dc_counts[dc] = dc_counts.get(dc, 0) + 1
        
        if len(dc_counts) > 1:
            max_dc = max(dc_counts.items(), key=lambda x: x[1])
            total = len(datacenters)
            concentration_pct = (max_dc[1] / total) * 100
            
            if concentration_pct > 70:
                patterns.append(f"📍 HIGH CONCENTRATION: {concentration_pct:.1f}% of resources in {max_dc[0]} (consider load distribution)")
            else:
                patterns.append(f"📍 BALANCED DISTRIBUTION: Resources spread across {len(dc_counts)} datacenters")
    
    # Time-based patterns (if created_at exists)
    if 'created_at' in results[0]:
        import re
        from datetime import datetime
        
        current_year = datetime.now().year
        dates = []
        for row in results:
            date_str = row.get('created_at')
            if date_str:
                # Extract year from various date formats
                year_match = re.search(r'20\d{2}', str(date_str))
                if year_match:
                    dates.append(int(year_match.group()))
        
        if dates:
            # Consider "recent" as current year or within last 6 months of previous year
            recent_threshold = current_year if datetime.now().month > 6 else current_year - 1
            recent_count = sum(1 for year in dates if year >= recent_threshold)
            
            if recent_count > len(dates) * 0.7:  # 70% threshold for significant growth
                patterns.append(f"📅 RECENT GROWTH: {(recent_count/len(dates)*100):.1f}% of resources created since {recent_threshold}")
            elif recent_count > len(dates) * 0.3:  # 30% threshold for moderate growth  
                patterns.append(f"📅 MODERATE GROWTH: {(recent_count/len(dates)*100):.1f}% of resources created since {recent_threshold}")
    
    return "\n".join(patterns) if patterns else "No significant operational patterns detected."


def format_pipeline_response(
    original_query: str = None,
    results: List[Dict] = None,
    sql_query: str = None,
    metadata: Dict[str, Any] = None,
    llm_summary: str = "",
    include_technical_details: bool = True
) -> str:
    """Format a complete pipeline response using the template."""
    
    # Format results section
    if results:
        formatted_results = f"Found {len(results)} matching records."
    else:
        formatted_results = "No results found for your query."
    
    response_parts = [
        llm_summary,
        "",
        f"**Results:** {formatted_results}",
    ]
    
    if include_technical_details:
        response_parts.extend([
            "",
            f"**SQL Query:**",
            f"```sql",
            sql_query,
            f"```",
            "",
            f"**Execution Time:** {metadata.get('execution_time_ms', 0):.2f}ms",
            f"**Tables Used:** {', '.join(metadata.get('tables_used', []))}",
        ])
    
    return "\n".join(response_parts)