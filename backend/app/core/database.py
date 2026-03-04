#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库配置和连接管理
"""

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import declarative_base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import QueuePool
    from app.core.config import settings
    
    # 创建异步引擎
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    
    # 创建异步会话工厂
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # 创建同步数据库引擎（用于某些同步操作）
    SYNC_DATABASE_URL = settings.DATABASE_URL.replace("mysql+aiomysql", "mysql+pymysql")
    sync_engine = create_engine(
        SYNC_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
    
    # 创建基类
    Base = declarative_base()
    
    DATABASE_AVAILABLE = True
except Exception as e:
    print(f"⚠️ 数据库模块未启用: {e}")
    DATABASE_AVAILABLE = False
    engine = None
    sync_engine = None
    AsyncSessionLocal = None
    SessionLocal = None
    Base = None


async def get_db():
    """获取数据库会话（主数据源）"""
    if not DATABASE_AVAILABLE:
        raise RuntimeError("数据库未配置")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_db_sync(use_secondary=False):
    """
    获取同步数据库会话（支持多数据源）
    
    Args:
        use_secondary: 是否使用第二数据源（宿主机数据库）
    
    Yields:
        Session: 数据库会话对象
    """
    if not DATABASE_AVAILABLE:
        raise RuntimeError("数据库未配置")
    
    if use_secondary:
        # 创建第二数据源的引擎和会话
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.config import settings
        
        if not hasattr(settings, 'MYSQL_HOST_2'):
            raise RuntimeError("第二数据源未配置")
        
        # 构建第二数据源 URL
        db_url_2 = f"mysql+pymysql://{settings.MYSQL_USER_2}:{settings.MYSQL_PASSWORD_2}@{settings.MYSQL_HOST_2}:{getattr(settings, 'MYSQL_PORT_2', 3306)}/{settings.MYSQL_DATABASE_2}?charset=utf8mb4"
        
        engine_2 = create_engine(db_url_2, pool_pre_ping=True)
        SessionLocal2 = sessionmaker(autocommit=False, autoflush=False, bind=engine_2)
        
        db = SessionLocal2()
        try:
            yield db
        finally:
            db.close()
    else:
        # 使用主数据源
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


async def init_db():
    """初始化数据库"""
    if not DATABASE_AVAILABLE:
        return
    async with engine.begin() as conn:
        # 创建所有表，checkfirst=True 避免表已存在的警告
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))


async def close_db():
    """关闭数据库连接"""
    if not DATABASE_AVAILABLE:
        return
    await engine.dispose()


def get_db_connection(use_secondary=False):
    """
    获取同步数据库连接（用于直接 SQL 操作）
    
    Args:
        use_secondary: 是否使用第二数据源（宿主机数据库）
    
    Returns:
        pymysql.Connection: 数据库连接对象
        
    Note:
        使用完毕后需要手动关闭连接：conn.close()
    """
    if not DATABASE_AVAILABLE:
        raise RuntimeError("数据库未配置")
    
    import pymysql
    from app.core.config import settings
    
    # 如果使用第二数据源
    if use_secondary:
        # 检查第二数据源配置
        if not hasattr(settings, 'MYSQL_HOST_2'):
            raise RuntimeError("第二数据源未配置，请在 .env 中添加 MYSQL_HOST_2 等配置")
        
        conn = pymysql.connect(
            host=settings.MYSQL_HOST_2,
            port=getattr(settings, 'MYSQL_PORT_2', 3306),
            user=settings.MYSQL_USER_2,
            password=settings.MYSQL_PASSWORD_2,
            database=settings.MYSQL_DATABASE_2,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.Cursor
        )
        return conn
    
    # 使用主数据源（原有逻辑）
    # 解析数据库 URL
    # 格式: mysql+aiomysql://user:password@host:port/database?charset=utf8mb4
    db_url = settings.DATABASE_URL.replace("mysql+aiomysql://", "").replace("mysql+pymysql://", "")
    
    # 分离认证信息和主机信息
    if "@" in db_url:
        auth_part, host_part = db_url.split("@", 1)
        user, password = auth_part.split(":", 1)
        
        # 分离主机和数据库（去除查询参数）
        if "/" in host_part:
            host_port, db_part = host_part.split("/", 1)
            # 去除查询参数（如 ?charset=utf8mb4）
            database = db_part.split("?")[0] if "?" in db_part else db_part
        else:
            host_port = host_part
            database = "cluster_management"
        
        # 分离主机和端口
        if ":" in host_port:
            host, port = host_port.split(":", 1)
            port = int(port)
        else:
            host = host_port
            port = 3306
    else:
        raise ValueError(f"Invalid DATABASE_URL format: {settings.DATABASE_URL}")
    
    # 创建连接
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.Cursor
    )
    
    return conn
