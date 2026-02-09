import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional

from exchangelib import Credentials, Account, Configuration as ExchangeConfig, DELEGATE, Q
from langchain_core.documents import Document


class EmailRetriever:
    """Retrieves emails directly from Exchange server using exchangelib."""
    
    # Cache structure: {username:query_hash: {"results": [Documents], "expires_at": timestamp}}
    _cache = {}
    CACHE_TTL = 300  # 5 minutes
    SEARCH_YEARS = 4  # Search last 4 years
    
    def __init__(self, username: str, password: str, email_address: str, server: str):
        """Initialize Exchange connection."""
        self.username = username
        self.email_address = email_address
        self.server = server
        
        try:
            credentials = Credentials(username=username, password=password)
            config = ExchangeConfig(server=server, credentials=credentials)
            self.account = Account(
                primary_smtp_address=email_address,
                config=config,
                autodiscover=False,
                access_type=DELEGATE
            )
        except Exception as e:
            print(f"[EmailRetriever] Failed to connect to Exchange: {e}")
            self.account = None
    
    def retrieve_emails(self, query: str, max_results: int = 5) -> list[Document]:
        """Search Exchange emails and return full emails as Documents."""

        if not self.account:
            print("[EmailRetriever] No Exchange account configured, skipping email search")
            return []
        
        cache_key = f"{self.username}:{hashlib.md5(query.lower().encode()).hexdigest()[:8]}"
        cached = self._get_cached(cache_key)
        if cached:
            print(f"[EmailRetriever] Using cached results for query: {query}")
            return cached[:max_results]
        
        try:
            keywords = [word.lower() for word in query.split() if len(word) > 2]
            if not keywords:
                return []
            
            since_date = datetime.now() - timedelta(days=365 * self.SEARCH_YEARS)
            
            # Build search query
            search_filters = []
            for keyword in keywords[:5]:
                search_filters.append(
                    Q(subject__icontains=keyword) | Q(body__icontains=keyword)
                )
            combined_filter = search_filters[0]
            for f in search_filters[1:]:
                combined_filter |= f
            
            # Execute search
            results = self.account.inbox.filter(
                combined_filter,
                datetime_received__gte=since_date
            ).order_by('-datetime_received')[:max_results * 2]  # Get more than needed for filtering
            
            # Convert to Documents
            documents = []
            for email in results:
                try:
                    # Format email content
                    content = self._format_email(email)
                    
                    # Filter by keyword relevance in content
                    content_lower = content.lower()
                    if not any(kw in content_lower for kw in keywords):
                        continue
                    
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": "Email",
                            "sender": str(email.sender) if email.sender else "Unknown",
                            "subject": str(email.subject) if email.subject else "No Subject",
                            "datetime_received": email.datetime_received.isoformat() if email.datetime_received else None,
                            "email_id": str(email.message_id) if hasattr(email, 'message_id') else None
                        }
                    )
                    documents.append(doc)
                    
                    if len(documents) >= max_results:
                        break
                        
                except Exception as e:
                    print(f"[EmailRetriever] Error processing email: {e}")
                    continue
            
            # Cache results
            self._set_cache(cache_key, documents)
            
            print(f"[EmailRetriever] Retrieved {len(documents)} emails for query: {query}")
            return documents
            
        except Exception as e:
            print(f"[EmailRetriever] Search failed: {e}")
            return []
    
    def _format_email(self, email) -> str:
        """Format email into readable text."""
        subject = str(email.subject) if email.subject else "No Subject"
        sender = str(email.sender) if email.sender else "Unknown"
        date = email.datetime_received.strftime("%Y-%m-%d %H:%M") if email.datetime_received else "Unknown"
        body = str(email.text_body) if email.text_body else (str(email.body) if email.body else "")
        
        return f"Subject: {subject}\nFrom: {sender}\nReceived: {date}\n\n{body}"
    
    def _get_cached(self, key: str) -> Optional[list[Document]]:
        """Get cached results if not expired."""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry["expires_at"]:
                return entry["results"]
            else:
                del self._cache[key]
        return None
    
    def _set_cache(self, key: str, results: list[Document]):
        """Cache results with TTL."""
        self._cache[key] = {
            "results": results,
            "expires_at": time.time() + self.CACHE_TTL
        }
        
        # Cleanup expired entries
        self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            k for k, v in self._cache.items() 
            if current_time >= v["expires_at"]
        ]
        for k in expired_keys:
            del self._cache[k]