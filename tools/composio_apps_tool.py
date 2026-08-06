"""
Composio Active App Tools for Jarvis AI Assistant.

Dedicated, typed LangChain tools for actively connected Composio apps:
  - Gmail           (fetch, send, search, draft)
  - Google Calendar (list events, create event)
  - Notion          (search pages, create page)
  - Google Sheets   (get values, append row)
  - Google Docs     (get document, create document)
  - Discord         (send message, fetch messages, create channel)

These tools call Composio's MCP HTTP endpoint directly using the shared helpers
from tools/composio_tool.py — no composio-core pip package needed.
"""

import json
from typing import Optional
from langchain_core.tools import tool
import config
from tools.composio_tool import _call_composio_mcp, _start_composio_session

logger = config.get_logger(__name__)


def _execute(tool_slug: str, intent: str, args: dict) -> dict:
    """Shared helper: starts a Composio session and executes one tool call."""
    session_id = _start_composio_session(intent)
    result = _call_composio_mcp("tools/call", {
        "name": "COMPOSIO_MULTI_EXECUTE_TOOL",
        "arguments": {
            "session_id": session_id,
            "current_step": 1,
            "total_steps": 1,
            "plan": intent,
            "tools": [{"tool_slug": tool_slug, "arguments": args}]
        }
    })
    if "error" in result:
        return {
            "status": "error",
            "summary": f"[{tool_slug}] Failed: {result['error']}",
            "data": {"tool_slug": tool_slug, "error": result["error"]}
        }
    try:
        content = result.get("result", {}).get("content", [{}])
        raw = content[0].get("text", str(result)) if content else str(result)
    except Exception:
        raw = str(result)
    return {
        "status": "success",
        "summary": f"[{tool_slug}] {intent}",
        "data": {"tool_slug": tool_slug, "result": raw}
    }


# ---------------------------------------------------------------------------
# 📧 Gmail Tools
# ---------------------------------------------------------------------------

@tool
def gmail_fetch_emails(
    max_results: int = 5,
    label: str = "INBOX"
) -> dict:
    """
    Fetches the most recent emails from a Gmail mailbox.

    Args:
        max_results: Number of emails to retrieve (default: 5).
        label: Gmail label to query — e.g. 'INBOX', 'SENT', 'UNREAD' (default: 'INBOX').

    Returns:
        dict with status, summary, and data containing email list.
    """
    logger.info(f"[Gmail] Fetching {max_results} emails from label '{label}'")
    return _execute(
        "GMAIL_FETCH_EMAILS",
        f"Fetch {max_results} most recent emails from {label}",
        {"max_results": max_results, "label_ids": [label], "user_id": "me"}
    )


@tool
def gmail_send_email(
    to: str,
    subject: str,
    body: str,
    cc: str = ""
) -> dict:
    """
    Sends an email via Gmail.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain text or HTML email body.
        cc: Optional CC email address (default: empty).

    Returns:
        dict with status, summary, and data containing the sent message ID.
    """
    logger.info(f"[Gmail] Sending email to '{to}': {subject}")
    args = {"to": to, "subject": subject, "body": body, "user_id": "me"}
    if cc:
        args["cc"] = cc
    return _execute("GMAIL_SEND_EMAIL", f"Send email to {to}: {subject}", args)


@tool
def gmail_search_emails(
    query: str,
    max_results: int = 10
) -> dict:
    """
    Searches Gmail using Gmail search syntax (e.g. 'from:boss@company.com subject:report').

    Args:
        query: Gmail search query string (supports all Gmail operators).
        max_results: Maximum number of results to return (default: 10).

    Returns:
        dict with status, summary, and data containing matched emails.
    """
    logger.info(f"[Gmail] Searching emails: '{query}'")
    return _execute(
        "GMAIL_FETCH_EMAILS",
        f"Search Gmail for: {query}",
        {"query": query, "max_results": max_results, "user_id": "me"}
    )


@tool
def gmail_create_draft(
    to: str,
    subject: str,
    body: str
) -> dict:
    """
    Creates a Gmail draft without sending it.

    Args:
        to: Draft recipient email address.
        subject: Draft subject line.
        body: Draft email body content.

    Returns:
        dict with status, summary, and draft ID.
    """
    logger.info(f"[Gmail] Creating draft to '{to}': {subject}")
    return _execute(
        "GMAIL_CREATE_EMAIL_DRAFT",
        f"Create Gmail draft to {to}: {subject}",
        {"to": to, "subject": subject, "body": body, "user_id": "me"}
    )


# ---------------------------------------------------------------------------
# 📅 Google Calendar Tools
# ---------------------------------------------------------------------------

@tool
def calendar_list_events(
    max_results: int = 10,
    calendar_id: str = "primary",
    time_min: str = ""
) -> dict:
    """
    Lists upcoming events from a Google Calendar.

    Args:
        max_results: Maximum number of events to return (default: 10).
        calendar_id: Calendar to query — use 'primary' for the main calendar (default: 'primary').
        time_min: ISO 8601 start time filter e.g. '2026-08-01T00:00:00Z' (default: now).

    Returns:
        dict with status, summary, and data containing event list.
    """
    logger.info(f"[GoogleCalendar] Listing {max_results} events from '{calendar_id}'")
    args: dict = {"max_results": max_results, "calendar_id": calendar_id}
    if time_min:
        args["time_min"] = time_min
    return _execute(
        "GOOGLECALENDAR_EVENTS_LIST",
        f"List {max_results} upcoming calendar events",
        args
    )


@tool
def calendar_create_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    calendar_id: str = "primary"
) -> dict:
    """
    Creates a new event in Google Calendar.

    Args:
        title: Event title/summary.
        start_datetime: ISO 8601 start datetime e.g. '2026-08-10T10:00:00Z'.
        end_datetime: ISO 8601 end datetime e.g. '2026-08-10T11:00:00Z'.
        description: Optional event description or agenda.
        calendar_id: Target calendar ID (default: 'primary').

    Returns:
        dict with status, summary, and created event ID.
    """
    logger.info(f"[GoogleCalendar] Creating event: '{title}' at {start_datetime}")
    args = {
        "summary": title,
        "start": {"dateTime": start_datetime},
        "end": {"dateTime": end_datetime},
        "calendar_id": calendar_id
    }
    if description:
        args["description"] = description
    return _execute("GOOGLECALENDAR_CREATE_EVENT", f"Create calendar event: {title}", args)


# ---------------------------------------------------------------------------
# 📓 Notion Tools
# ---------------------------------------------------------------------------

@tool
def notion_search_pages(query: str = "") -> dict:
    """
    Searches your Notion workspace for pages, databases, or blocks.

    Args:
        query: Search query string. Leave empty to list all recent pages.

    Returns:
        dict with status, summary, and matching Notion pages/databases.
    """
    logger.info(f"[Notion] Searching pages: '{query or '(all)'}'")
    return _execute(
        "NOTION_SEARCH_NOTION_PAGE",
        f"Search Notion workspace for: {query or 'all pages'}",
        {"query": query} if query else {}
    )


@tool
def notion_create_page(
    title: str,
    content: str,
    parent_page_id: str = ""
) -> dict:
    """
    Creates a new page in your Notion workspace.

    Args:
        title: Page title.
        content: Page body content (plain text or markdown-like syntax).
        parent_page_id: Optional Notion page ID to nest under. Leave empty for root workspace.

    Returns:
        dict with status, summary, and the created page URL.
    """
    logger.info(f"[Notion] Creating page: '{title}'")
    args: dict = {
        "title": title,
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": [{"object": "block", "type": "paragraph",
                       "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]}}]
    }
    if parent_page_id:
        args["parent"] = {"type": "page_id", "page_id": parent_page_id}
    return _execute("NOTION_CREATE_PAGE", f"Create Notion page: {title}", args)


# ---------------------------------------------------------------------------
# 📊 Google Sheets Tools
# ---------------------------------------------------------------------------

@tool
def sheets_get_values(
    spreadsheet_id: str,
    range_name: str = "Sheet1!A1:Z100"
) -> dict:
    """
    Reads cell values from a Google Sheets spreadsheet.

    Args:
        spreadsheet_id: The Google Sheets spreadsheet ID (from the URL).
        range_name: A1 notation range to read e.g. 'Sheet1!A1:D10' (default: full Sheet1).

    Returns:
        dict with status, summary, and the cell values as a 2D array.
    """
    logger.info(f"[GoogleSheets] Reading range '{range_name}' from spreadsheet '{spreadsheet_id}'")
    return _execute(
        "GOOGLESHEETS_BATCH_GET",
        f"Read Google Sheets data: {spreadsheet_id} range {range_name}",
        {"spreadsheet_id": spreadsheet_id, "ranges": [range_name]}
    )


@tool
def sheets_append_row(
    spreadsheet_id: str,
    values: str,
    range_name: str = "Sheet1!A1",
    sheet_name: str = "Sheet1"
) -> dict:
    """
    Appends a new row of data to a Google Sheets spreadsheet.

    Args:
        spreadsheet_id: The Google Sheets spreadsheet ID (from the URL).
        values: JSON array string of row values e.g. '["2026-08-05", "PCB Audit", "PASSED"]'.
        range_name: Target range in A1 notation where data will be appended (default: 'Sheet1!A1').
        sheet_name: Sheet tab name (default: 'Sheet1').

    Returns:
        dict with status, summary, and updated row count.
    """
    logger.info(f"[GoogleSheets] Appending row to '{spreadsheet_id}' sheet '{sheet_name}'")
    try:
        row = json.loads(values)
    except json.JSONDecodeError:
        row = [values]
    return _execute(
        "GOOGLESHEETS_SHEET_FROM_SPREADSHEET_APPEND_GOOGLE_SHEET_VALUES",
        f"Append row to Google Sheet {spreadsheet_id}",
        {"spreadsheet_id": spreadsheet_id, "range": range_name, "values": [row], "sheet_name": sheet_name}
    )


# ---------------------------------------------------------------------------
# 📄 Google Docs Tools
# ---------------------------------------------------------------------------

@tool
def docs_get_document(document_id: str) -> dict:
    """
    Retrieves the full content of a Google Docs document.

    Args:
        document_id: The Google Docs document ID (from the URL).

    Returns:
        dict with status, summary, and document body content.
    """
    logger.info(f"[GoogleDocs] Getting document: '{document_id}'")
    return _execute(
        "GOOGLEDOCS_GET_DOCUMENT",
        f"Get Google Docs document: {document_id}",
        {"document_id": document_id}
    )


@tool
def docs_create_document(
    title: str,
    content: str = ""
) -> dict:
    """
    Creates a new Google Docs document.

    Args:
        title: Document title.
        content: Optional initial plain text content to insert into the document.

    Returns:
        dict with status, summary, and the new document ID and URL.
    """
    logger.info(f"[GoogleDocs] Creating document: '{title}'")
    args: dict = {"title": title}
    if content:
        args["text"] = content
    return _execute("GOOGLEDOCS_CREATE_DOCUMENT", f"Create Google Doc: {title}", args)


# ---------------------------------------------------------------------------
# 💬 Discord Tools (Composio Integration)
# ---------------------------------------------------------------------------

@tool
def discord_send_message(
    channel_id: str,
    message: str
) -> dict:
    """
    Sends a message to a Discord text channel via Composio connection.

    Args:
        channel_id: The Discord text channel ID (or channel name/topic).
        message: Plain text or formatted markdown message content to post.

    Returns:
        dict with status, summary, and data containing Discord API delivery output.
    """
    logger.info(f"[Discord] Sending message to channel '{channel_id}'")
    return _execute(
        "DISCORDBOT_CREATE_MESSAGE",
        f"Send Discord message to channel {channel_id}",
        {"channel_id": channel_id, "content": message}
    )


@tool
def discord_fetch_messages(
    channel_id: str,
    limit: int = 5
) -> dict:
    """
    Fetches the most recent messages from a Discord text channel via Composio.

    Args:
        channel_id: The Discord text channel ID.
        limit: Number of recent messages to retrieve (default: 5).

    Returns:
        dict with status, summary, and data containing recent channel messages.
    """
    logger.info(f"[Discord] Fetching {limit} messages from channel '{channel_id}'")
    return _execute(
        "DISCORDBOT_GET_MESSAGES",
        f"Fetch {limit} recent Discord messages from channel {channel_id}",
        {"channel_id": channel_id, "limit": limit}
    )


@tool
def discord_create_channel(
    guild_id: str,
    channel_name: str
) -> dict:
    """
    Creates a new text channel in a Discord server (guild) via Composio.

    Args:
        guild_id: The Discord server/guild ID.
        channel_name: Name of the new channel to create.

    Returns:
        dict with status, summary, and new channel details.
    """
    logger.info(f"[Discord] Creating channel '{channel_name}' in guild '{guild_id}'")
    return _execute(
        "DISCORDBOT_GUILD_CHANNEL_CREATE",
        f"Create Discord channel '{channel_name}' in server {guild_id}",
        {"guild_id": guild_id, "name": channel_name}
    )
