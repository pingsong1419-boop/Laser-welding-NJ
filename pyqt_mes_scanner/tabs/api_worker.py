# -*- coding: utf-8 -*-
"""公共异步 HTTP Worker，用于获取工单 + 工步下发 (已切换至 MesService)"""
from PyQt5.QtCore import QThread, pyqtSignal
from services.mes_service import MesService
import time
from datetime import datetime


class WorkerThread(QThread):
    finished = pyqtSignal(object, object, object)  # order_data, route_data, order_info
    error = pyqtSignal(str)
    api_record = pyqtSignal(dict)

    def __init__(self, url, payload, route_url, route_work_seq_no, order_info=None, skip_implicit_route=False):
        super().__init__()
        self.url = url
        self.payload = payload
        self.route_url = route_url
        self.route_work_seq_no = route_work_seq_no
        self.order_info = order_info
        self.skip_implicit_route = skip_implicit_route

    def _emit_record(self, title, url, req_body, res_body, start_time):
        dur = int((time.time() - start_time) * 1000)
        status = "success" if MesService._is_success(res_body) else "error"
        self.api_record.emit({
            "title": title,
            "status": status,
            "time": datetime.now().strftime("%H:%M:%S"),
            "duration": dur,
            "url": url,
            "reqBody": req_body,
            "resBody": res_body
        })

    def run(self):
        try:
            if self.order_info is None:
                # 获取工单
                start = time.time()
                order_data = MesService.get_order(self.url, self.payload)
                self._emit_record("获取工单", self.url, self.payload, order_data, start)

                if not MesService._is_success(order_data):
                    err_msg = order_data.get("message", "未知错误")
                    self.error.emit(f"获取工单失败|{err_msg}")
                    return

                datas = order_data.get("datas", []) or order_data.get("data", [])
                
                # 如果开启了跳过隐式工步下发，则不论工单数量是多少，一律直接包装为列表返回，杜绝默默执行的多余工步下发
                if getattr(self, "skip_implicit_route", False):
                    if isinstance(datas, dict):
                        datas = [datas]
                    self.finished.emit(order_data, None, datas)
                    return

                if isinstance(datas, list) and len(datas) > 1:
                    self.finished.emit(order_data, None, datas)
                    return
                elif isinstance(datas, list) and len(datas) > 0:
                    order_info = datas[0]
                elif isinstance(datas, dict):
                    order_info = datas
                else:
                    self.error.emit("获取工单失败|响应中未找到工单数据")
                    return
            else:
                order_info = self.order_info
                order_data = {"code": 200, "datas": [order_info]}

            # 工步下发
            route_code = order_info.get("routeCode") or order_info.get("route_No", "")
            start = time.time()
            route_data = MesService.get_route(self.route_url, route_code, self.route_work_seq_no)
            route_payload = {"routeCode": route_code, "workSeqNo": self.route_work_seq_no}
            self._emit_record("工步下发", self.route_url, route_payload, route_data, start)

            self.finished.emit(order_data, route_data, order_info)

        except Exception as e:
            self.error.emit(f"网络异常|无法连接 MES 服务器:\n{str(e)}")
