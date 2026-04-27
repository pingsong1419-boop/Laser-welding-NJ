# -*- coding: utf-8 -*-
"""MES 统一接口交互服务"""
import requests
import time

class MesService:
    @staticmethod
    def _is_success(resp):
        """统一判断 API 响应是否成功 (code=200 为成功)"""
        if not resp:
            return False
        code = resp.get("code")
        if code is not None:
            return code == 200
        return resp.get("success") is not False

    @staticmethod
    def _get_headers():
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

    @classmethod
    def post(cls, url, payload, timeout=30):
        """核心 POST 基础网络封装"""
        try:
            response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=timeout)
            if response.status_code == 200:
                return response.json()
            return {"code": response.status_code, "message": f"HTTP 错误: {response.status_code}", "success": False}
        except Exception as e:
            return {"code": 500, "message": str(e), "success": False}

    @classmethod
    def get_order(cls, url, payload):
        """① 获取工单接口"""
        return cls.post(url, payload)

    @classmethod
    def get_route(cls, url, route_code, work_seq_no):
        """② 工步下发接口"""
        payload = {
            "routeCode": route_code,
            "workSeqNo": work_seq_no
        }
        return cls.post(url, payload)

    @classmethod
    def check_single_material(cls, url, payload):
        """③ 单物料校验接口"""
        return cls.post(url, payload)

    @classmethod
    def check_full_material(cls, url, payload):
        """④ 全物料校验接口"""
        return cls.post(url, payload)

    @classmethod
    def upload_module_bind(cls, url, payload):
        """⑤ 模块绑定模组数据上传 (预留真实，目前为 Mock)"""
        # return cls.post(url, payload)
        return {"code": 200, "success": True, "message": "模拟模块绑定上传成功"}

    @classmethod
    def upload_pack_box(cls, url, payload):
        """⑥ 模组入箱位置信息上传 (预留真实，目前为 Mock)"""
        # return cls.post(url, payload)
        return {"code": 200, "success": True, "message": "模拟入箱顺序上传成功"}
