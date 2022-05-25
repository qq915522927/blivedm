# -*- coding: utf-8 -*-
import json
import os
import asyncio
import aiofiles
from aiohttp import ClientSession
import random

import blivedm

import struct

header_packer = struct.Struct('I')

USER_PHOTO_DIR = './user_photos'

async def main():
    await run_single_client()

async def run_single_client():
    """
    演示监听一个直播间
    """
    # room_id = 5520
    room_id = 7777
    # room_id = 6
    # 如果SSL验证失败就把ssl设为False，B站真的有过忘续证书的情况
    client = blivedm.BLiveClient(room_id, ssl=True)
    handler = MyHandler()
    client.add_handler(handler)

    client.start()
    try:
        # 演示5秒后停止
        # await asyncio.sleep()
        # client.stop()

        await client.join()
    finally:
        await client.stop_and_close()


class MyHandler(blivedm.BaseHandler):
    # # 演示如何添加自定义回调
    # _CMD_CALLBACK_DICT = blivedm.BaseHandler._CMD_CALLBACK_DICT.copy()
    #
    # # 入场消息回调
    # async def __interact_word_callback(self, client: blivedm.BLiveClient, command: dict):
    #     print(f"[{client.room_id}] INTERACT_WORD: self_type={type(self).__name__}, room_id={client.room_id},"
    #           f" uname={command['data']['uname']}")
    # _CMD_CALLBACK_DICT['INTERACT_WORD'] = __interact_word_callback  # noqa

    async def _on_heartbeat(self, client: blivedm.BLiveClient, message: blivedm.HeartbeatMessage):
        print(f'[{client.room_id}] 当前人气值：{message.popularity}')

    async def _on_danmaku(self, client: blivedm.BLiveClient, message: blivedm.DanmakuMessage):
        loop = asyncio.get_event_loop()
        loop.create_task(
            self._on_danmaku_no_wait(client, message)
        )

    async def _on_danmaku_no_wait(self, client: blivedm.BLiveClient, message: blivedm.DanmakuMessage):
        print(f'[{client.room_id}] {message.uname}[{message.uid}]：{message.msg}')

        if not getattr(self, 'tcp_writer', None):
            fut = asyncio.open_connection( '127.0.0.1', 8052)
            reader, writer =  await asyncio.wait_for(fut, timeout=1)
            print('init connection')

            self.tcp_writer = writer
        face_path = os.path.abspath(os.path.join(USER_PHOTO_DIR, f'{message.uid}.jpg'))
        if not os.path.exists(
            face_path
        ):
            user_info = await get_user_info(message.uid)
            if user_info:
                face_path = await download_user_photo(message.uid, user_info['face'])
            else:
                face_path = os.path.abspath(os.path.join(USER_PHOTO_DIR, '0.png'))

        danmu_data = {
            "uid": message.uid,
            "uname": message.uname,
            "msg": message.msg,
            "face_path": face_path,
        }

        dumped_message: bytes = json.dumps(danmu_data).encode('utf-8')
        packed_header = header_packer.pack(len(dumped_message))
        try:
            self.tcp_writer.write(packed_header+dumped_message)
            await self.tcp_writer.drain()
            print("sending...")
        except Exception as e:
            self.tcp_writer.close()
            self.tcp_writer = None
            print(f"Fail to send message to server, {e}")


    async def _on_gift(self, client: blivedm.BLiveClient, message: blivedm.GiftMessage):
        print(f'[{client.room_id}] {message.uname} 赠送{message.gift_name}x{message.num}'
              f' （{message.coin_type}瓜子x{message.total_coin}）')

    async def _on_buy_guard(self, client: blivedm.BLiveClient, message: blivedm.GuardBuyMessage):
        print(f'[{client.room_id}] {message.username} 购买{message.gift_name}')

    async def _on_super_chat(self, client: blivedm.BLiveClient, message: blivedm.SuperChatMessage):
        print(f'[{client.room_id}] 醒目留言 ¥{message.price} {message.uname}：{message.message}')


async def get_user_info(uid):
    url = f"https://api.bilibili.com/x/space/acc/info?mid={uid}&jsonp=jsonp"
    async with ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data.get("code") == 0:
            # self.info['ban'] = bool(response['data']['silence'])
            # self.info['coins'] = response['data']['coins']
            # self.info['experience']['current'] = response['data']['level_exp']['current_exp']
            # self.info['experience']['next'] = response['data']['level_exp']['next_exp']
            # self.info['face'] = response['data']['face']
            # self.info['level'] = response['data']['level']
            # self.info['nickname'] = response['data']['name']
            # # self._log(f"{self.info['nickname']}(UID={self.get_uid()}), Lv.{self.info['level']}({self.info['experience']['current']}/{self.info['experience']['next']}), 拥有{self.info['coins']}枚硬币, 账号{'状态正常' if not self.info['ban'] else '被封禁'}")
                return data['data']
            else:
                # print(data)
                return None



async def download_user_photo(uid, url):
    async with ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.read()

    fname = f'{uid}.jpg'
    file_path = os.path.join(USER_PHOTO_DIR, fname)
    async with aiofiles.open(
           file_path, "wb"
        ) as outfile:
            await outfile.write(data)

    return os.path.abspath(file_path)



if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
