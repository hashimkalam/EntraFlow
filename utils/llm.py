"""LLM utility for initializing LangChain models."""

import os
from typing import Any, Dict, Optional
from langchain_huggingface import HuggingFacePipeline
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from utils.config import Config
from utils.logger import get_logger

logger = get_logger("LLMUtils")

def get_llm(config: Optional[Config] = None):
    """
    Initialize a LangChain LLM based on configuration.
    
    Args:
        config: Configuration object
        
    Returns:
        LangChain LLM instance
    """
    config = config or Config()
    llm_settings = config.get('api', 'langchain', default={})
    
    provider = llm_settings.get('provider', 'huggingface').lower()
    model_name = llm_settings.get('model_name', 'google/gemma-2b-it')
    temperature = llm_settings.get('temperature', 0.7)
    max_tokens = llm_settings.get('max_tokens', 512)
    
    logger.info(f"Initializing LLM provider: {provider} (model: {model_name})")
    
    try:
        if provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("OPENAI_API_KEY not found in environment. Falling back to HuggingFace.")
                return _get_huggingface_llm(model_name, temperature, max_tokens)
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key
            )
        
        elif provider == 'ollama':
            return Ollama(
                model=model_name,
                temperature=temperature,
            )
        
        else: # Default to HuggingFace
            return _get_huggingface_llm(model_name, temperature, max_tokens)
            
    except Exception as e:
        logger.error(f"Failed to initialize LLM {provider}: {str(e)}")
        # Ultimate fallback to a small local model via HF
        return _get_huggingface_llm('gpt2', temperature, 128)

def _get_huggingface_llm(model_name: str, temperature: float, max_tokens: int):
    """Initialize a local HuggingFace model via LangChain."""
    try:
        from transformers import pipeline, AutoTokenizer
        import torch
        
        # Force CPU for stability in limited environments
        device = -1
        
        # Load tokenizer to get pad_token
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            
        pipe = pipeline(
            "text-generation",
            model=model_name,
            tokenizer=tokenizer,
            device=device,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=temperature,
            truncation=True,
            pad_token_id=tokenizer.pad_token_id
        )
        
        return HuggingFacePipeline(pipeline=pipe)
    except Exception as e:
        logger.error(f"Failed to load HuggingFace model {model_name}: {str(e)}")
        raise
