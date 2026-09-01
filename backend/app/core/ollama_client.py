"""
Ollama 客户端
封装与 Ollama 服务的所有交互
"""

import requests
import json
from typing import Optional, List, Dict, Any, Generator

from app.utils.logger import logger
from config.settings import Config


class OllamaClient:
    """Ollama API 客户端"""

    def __init__(self, host: Optional[str] = None):
        """
        初始化 Ollama 客户端

        Args:
            host: Ollama 服务地址，默认从配置读取
        """
        self.host = host or Config.OLLAMA_HOST
        self.base_url = self.host.rstrip('/')
        self.default_model = Config.DEFAULT_MODEL
        self.timeout = 120  # 请求超时时间（秒）

        logger.info(f"Ollama 客户端初始化完成，服务地址: {self.base_url}")

    def _post(self, endpoint: str, payload: Dict[str, Any], stream: bool = False) -> Dict[str, Any]:
        """
        发送 POST 请求到 Ollama API

        Args:
            endpoint: API 端点（如 '/api/generate'）
            payload: 请求体
            stream: 是否流式响应

        Returns:
            API 响应内容（如果是流式，返回完整拼接后的结果）
        """
        url = f"{self.base_url}{endpoint}"

        try:
            if stream:
                # 流式响应
                response = requests.post(
                    url,
                    json=payload,
                    stream=True,
                    timeout=self.timeout
                )
                response.raise_for_status()

                # 拼接流式响应
                full_content = ""
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        try:
                            data = json.loads(line)
                            if 'response' in data:
                                full_content += data['response']
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue

                return {'response': full_content, 'done': True}
            else:
                # 非流式响应
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()

        except requests.exceptions.ConnectionError:
            logger.error(f"无法连接到 Ollama 服务: {self.base_url}")
            raise Exception(f"无法连接到 Ollama 服务，请确保 Ollama 已启动并运行在 {self.base_url}")
        except requests.exceptions.Timeout:
            logger.error(f"Ollama 请求超时: {url}")
            raise Exception("Ollama 请求超时，请检查模型是否正在加载或系统资源是否充足")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Ollama HTTP 错误: {e}")
            raise Exception(f"Ollama 服务返回错误: {e}")
        except Exception as e:
            logger.error(f"Ollama 请求失败: {str(e)}")
            raise Exception(f"请求 Ollama 服务失败: {str(e)}")

    def generate(
            self,
            prompt: str,
            model: Optional[str] = None,
            system: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            stream: bool = False
    ) -> str:
        """
        文本生成（单轮）

        Args:
            prompt: 输入提示词
            model: 模型名称，默认使用配置的默认模型
            system: 系统提示词（可选）
            temperature: 温度参数，默认从配置读取
            max_tokens: 最大生成 token 数，默认从配置读取
            stream: 是否流式返回

        Returns:
            生成的文本内容
        """
        model_name = model or self.default_model
        temp = temperature if temperature is not None else Config.TEMPERATURE
        max_tok = max_tokens if max_tokens is not None else Config.MAX_TOKENS

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": stream,
            "temperature": temp,
            "max_tokens": max_tok,
            "options": {
                "num_predict": max_tok,
                "temperature": temp
            }
        }

        if system:
            payload["system"] = system

        logger.debug(f"调用 generate: model={model_name}, prompt_len={len(prompt)}, temp={temp}")

        result = self._post("/api/generate", payload, stream=stream)

        if stream:
            content = result.get('response', '')
        else:
            content = result.get('response', '')

        logger.debug(f"生成完成: content_len={len(content)}")
        return content

    def chat(
            self,
            messages: List[Dict[str, str]],
            model: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            stream: bool = False
    ) -> str:
        """
        多轮对话

        Args:
            messages: 消息列表，格式: [{"role": "user/assistant/system", "content": "..."}]
            model: 模型名称，默认使用配置的默认模型
            temperature: 温度参数，默认从配置读取
            max_tokens: 最大生成 token 数，默认从配置读取
            stream: 是否流式返回

        Returns:
            AI 回复的文本内容
        """
        model_name = model or self.default_model
        temp = temperature if temperature is not None else Config.TEMPERATURE
        max_tok = max_tokens if max_tokens is not None else Config.MAX_TOKENS

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_predict": max_tok,
                "temperature": temp
            }
        }

        logger.debug(f"调用 chat: model={model_name}, messages_count={len(messages)}, temp={temp}")

        result = self._post("/api/chat", payload, stream=stream)

        if stream:
            content = result.get('message', {}).get('content', '')
        else:
            content = result.get('message', {}).get('content', '')

        logger.debug(f"对话完成: content_len={len(content)}")
        return content

    def list_models(self) -> List[str]:
        """
        获取已安装的模型列表

        Returns:
            模型名称列表
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            logger.debug(f"获取模型列表成功: {models}")
            return models

        except Exception as e:
            logger.error(f"获取模型列表失败: {str(e)}")
            return []

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        获取模型详细信息

        Args:
            model_name: 模型名称

        Returns:
            模型信息字典，如果不存在则返回 None
        """
        try:
            url = f"{self.base_url}/api/show"
            payload = {"model": model_name}
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"获取模型信息失败: {str(e)}")
            return None

    def check_health(self) -> bool:
        """
        检查 Ollama 服务是否可用

        Returns:
            True 表示服务可用，False 表示不可用
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"Ollama 服务健康检查失败: {str(e)}")
            return False