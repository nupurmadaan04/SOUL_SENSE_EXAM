import pytest
from api.services.security_service import SecurityService

def test_is_disposable_email_exact_match():
    # Test domains from the provided JSON list
    assert SecurityService.is_disposable_email("user@mailinator.com") is True
    assert SecurityService.is_disposable_email("test@guerrillamail.com") is True
    assert SecurityService.is_disposable_email("admin@temp-mail.org") is True

def test_is_disposable_email_subdomain_match():
    # Test subdomains of disposable providers
    assert SecurityService.is_disposable_email("user@sub.mailinator.com") is True
    assert SecurityService.is_disposable_email("test@part.guerrillamail.com") is True

def test_is_disposable_email_legitimate():
    # Test legitimate domains
    assert SecurityService.is_disposable_email("user@gmail.com") is False
    assert SecurityService.is_disposable_email("dev@outlook.com") is False
    assert SecurityService.is_disposable_email("info@google.com") is False

def test_is_disposable_email_malformed():
    # Test malformed emails
    assert SecurityService.is_disposable_email("not-an-email") is False
    assert SecurityService.is_disposable_email(None) is False
    assert SecurityService.is_disposable_email("") is False
