from data.db import declare_database, Base
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, Integer, Text


class Block(Base):
    __tablename__ = 'block'
    number = Column(Integer, primary_key=True)  # 区块号
    hash = Column(String(256), unique=True, nullable=False)  # 哈希值
    timestamp = Column(Integer, nullable=False)  # 时间戳
    transactions = Column(Text)  # 交易的哈希值拼接而成的字符串


# 创建表
async def create_table():
    db = declare_database(url='sqlite+aiosqlite:////data/web3.db')
    async with db() as session:
        await session.execute(sa.schema.CreateTable(Block.__table__))
        await session.commit()
        await session.close()


# 根据区块号获取区块数据
async def get_block(number):
    db = declare_database(url='sqlite+aiosqlite:////data/web3.db')
    async with db() as session:
        result_query = await session.execute(sa.select(Block).where(Block.number == number))
        result = result_query.scalar()
        return result


# 插入区块数据（单/多均可插入）
async def insert_block(block):
    print("任务开始执行")
    db = declare_database(url='sqlite+aiosqlite:////data/web3.db')
    async with db() as session:
        try:
            result = await session.execute(sa.insert(Block).values(block))
            print("影响行数：", result.rowcount)
            # session.add(Block(**block))
            await session.commit()
            print("插入数据成功")
        except Exception as e:
            await session.rollback()
            raise e


# 获取特定区间范围内的区块数据
async def get_blocks(start: int, end: int):
    db = declare_database(url='sqlite+aiosqlite:////data/web3.db')
    async with db() as session:
        # 获取区间范围内的区块数据
        result_query = await session.execute(sa.select(Block).where(Block.number.between(start, end)))
        results = result_query.scalars().all()
        block_list = []
        for result in results:
            block_list.append(result.as_dict())
        # print(block_list)
        await session.close()
    return block_list


# 按照时间戳倒序，获取最新的100条区块数据
async def query():
    db = declare_database(url='sqlite+aiosqlite:////data/web3.db')
    async with db() as session:
        # 获取区间范围内的区块数据
        result_query = await session.execute(sa.select(Block).order_by(Block.timestamp).limit(100))
        results = result_query.scalars().all()
        block_list = []
        for result in results:
            block_list.append(result.as_dict())
        # print(block_list)
        await session.close()
    return block_list


if __name__ == '__main__':
    import asyncio

    # asyncio.run(create_table())
    # asyncio.run(get_blocks(1, 100))

    # block = {'number': 22106262, 'hash': '68f9e76589c52c2ed15a1f9d9258c161ab7c313bc4ef2a68fd4479624fb954d8',
    #          'timestamp': 1742692823,
    #          'transactions': 'd83d14cd5dc31d014d4b3b2d0698b18e40bf9b443842e5504a70a98abd0506ea,d88aee653db10ee318fea5dc9201f2d51b6b99bb3419865426f240f1d3e27621,465904f50aff935d4cc73453846502bbc600ba469f8d032b2f4e3b015a7b49d9,ce86d01352913606ecf10ae20f2fc4dd3072205347cd71ae3aee9786bac6b9cd,f2add1693dbf8c8fd63635432a04f412df491d596ab9f2fee74a341642530660,59bb6d7b8a3b2d7577e5e3ccbe42e0c46b56c18434ffe813d6a6a7ed5b343b4f,c3984da36aa456a767e47d530652fa1853822553c62736a81d1d6c7f4f82f055,d76eed0149f42fc912dacf02b1a7ebd6ef280e1dced19933a7ba7e385e0829fb,6cad2c033e2206f14babb4b13bb97b69a9a82be9af21d2d213c704b3142b3e6b,276eb04c419eb88e674dfccbe6bed3e8848a75d74b765b9f9d8b35450890ed68,7f3a663b7ee3ba73f00f90c4baeed2f63d1b31c4ca75b33a2f7f4bc203392135,0e0a0e687838bfc887d75178afd4b685a5c0ff65801f59e9fbc0923daace575e,3c80ff559e9843e66ed2c56dd56a724502d76c02e2ac73c1da0deab3fb60f22d,b88149a263aba5a34f6bc181603da03786d26e8474b5ee77651a4a0b97766257,8f105718a43648e05814d2a4e55da55a2da41c56b631d8ffc9dec2733313a89d,7073bd8fa8ee980d588e3e2d18bf373c2a74b8a00763f993c5b130e42d0f5700,1a692e36f5b09eccbf5b18cad9e7dc419f02a76de37cde81f07fc6386949de6d,a765b9952ccaf2484da2aa68f1e09c41ed85042d4b662444477da2f79dd37fc8,47186deb30f77fc8b6240522e0126bd4b054f48fcc2046fee902526784db026d,07df4473e4922956bbe126a316c5a4283279f0cbeda10c5851c2eb93eba28fbf,f15453e318d7afff9e1c30a06fb07956e11f1fc4c23ed5c66e7a9f67e2ea4792,fafec13d6fcf576aeddaf019152ec1a412b128d12b4ef6fbbfd9557eee6a41d8,82a17173c68bf5fe1f2f19d2f078497516bda81dd525ef7163426c2d4dbe1d3c,a9871920ba9895bb4610b0171869f9722940bdbb081582d39546d59a716fa000,f7fa497bbf83672f2a7477605c545f6bd28c9d53e5257bafbe832669452eeb6f,e708ff3dd2921bd4a5d5a0a9fbda9c8dba2751f96966792b74ca8dd50e5f42d7,7dfc41e78afdfa7699604b506a403b55d2626cfc451980c9f1698630ab84437e,c26d38fed0b6058135e5ca0ae365ace01e92ca241f5077ed2295122208618160,153877caf161fbe1879c422d5a2be55270ca557202ad74a76f018a3d4d5c45e3,4b42be317bce42db5a82df54b40a3f50bba25be94af3bf7ab31458e6a364b33a,5075ee3ca0b42d7ddffa9e5c2e5ee3b52065ada37676c68cd8f4521028741472,586b6b1f7202515106fc862b56c2631479f054742344981d4821a787b81e704c,7a0e199109c8841f37e9644f66eb5a7ef6f3fa3e8325fdf9b3cdb4aaae4e1c5d,7cd20ee39134572a7534b2d3a09562b72b2f27ecbb3d15bec7684123fc09e941,87f90bb3441b844a3ad3310a4a5953542effee28d71d49d3d86198f925118e57,8bc55a5e24b42a6b574c05d9f8b409168bdfa08b4bce9b8c479ffec03fa29570,9a6911c75301b26f9b5cf23c69a91db4b6252ca30ed293b16175f3db907f9092,f4f920e96f8fc2be36b8366157cce2986f31a601eca9ecede2843bfe40924672,f9af5f4607909795fa485486c2532e84c333e59b3c485837f884de99d5178cf7,fe9dde138b6e10b050f78c5c6551b5884877d447bea0319d817c1e0ef377df75,c5f4ed8d9c4f5707a9ffcadaea12faa56a2e36fefcd429a2d0afd8922e8098e5,4af1f839fae22a28082c5e61f8c44fa1aeadff8730041a55af6db880713f0d83,b60368bc50c30a55bee5475dbce80a822950ebf1b44d4c53ae3b08001578f4d8,5e498c5ae08ff8a804dc370a57bffe2274796771690bdc604354d9e934e956ac,d2a658a166965bd4947c0a5ebb01b51c9028d7ac73e8c0365057a637ba6f9051,a85dd66e3b76b24f03183b7f8c7a41d85cbfb34be1019a5c595d40f52f7a466d,3d13a99cae091b8c01b4f473e35d65592d84c0eb71f818f35ee53fe5a5794a47,9e97c3b94d5b9fed97c34fd920cfa65387b8ee992fb52ecb0046898d20c81c40,e062ab9643cf723bd2ac02d22c99f42da953e765968825139278ba18334d3588,21c894411333b0a976fd070613e7956c4ba846c20e6c205f30bd4747d6178efb,18dd954218e6e51adbb82e493e4eed57a7b8a95b6f828dec8578cace78278c04,2c54dd4e3843baa1ddc826741c03343b1f3dca1baaf214049aa36a5af68eb7d4,c06702c266611eb32ddead9807ada60d6f4874c90426b370cb478ed8a240847e,f12dcac8680298b821186712484e2d1f6f18646076b4a80147a1140184e33789,5b1f2d2c58f360f13091abde53ddf5c5c20ae87149d39deac31ec5a385236e51,9a662246a14afd210aac453fb91479dd76813c1dd3152dd0f72a98b451fac3a0,e3cc3bf3d41a83737c2ce1464f709d34adae18a1d82114188469dcfb8201d698,37a56dc8edf78b56ef273e6d01aaf97e5b342e5aa4b997f23e5e57465bfec434'}
    # asyncio.run(insert_block(block))
