UP_SQL = """
IF OBJECT_ID(N'[shopease].[products]', N'U') IS NULL
BEGIN
    CREATE TABLE [shopease].[products] (
        [id] int IDENTITY(1,1) NOT NULL
            CONSTRAINT [PK_products] PRIMARY KEY CLUSTERED,
        [name] nvarchar(100) NOT NULL,
        [description] nvarchar(1000) NULL,
        [price] decimal(19,4) NOT NULL,
        [stock_quantity] int NOT NULL,
        [category] nvarchar(100) COLLATE Latin1_General_100_CI_AS NOT NULL,
        [status] nvarchar(8) NOT NULL,
        [created_at] datetimeoffset(7) NOT NULL
            CONSTRAINT [DF_products_created_at] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [CK_products_price_positive] CHECK ([price] > 0),
        CONSTRAINT [CK_products_stock_nonnegative] CHECK ([stock_quantity] >= 0),
        CONSTRAINT [CK_products_status] CHECK ([status] IN (N'Active', N'Inactive'))
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE [object_id] = OBJECT_ID(N'[shopease].[products]')
      AND [name] = N'IX_products_category_id'
)
    CREATE NONCLUSTERED INDEX [IX_products_category_id]
        ON [shopease].[products] ([category], [id]);
"""

VERIFY_SQL = """
SELECT CASE WHEN
    OBJECT_ID(N'[shopease].[products]', N'U') IS NOT NULL
    AND (
        SELECT COUNT(*)
        FROM sys.columns
        WHERE [object_id] = OBJECT_ID(N'[shopease].[products]')
    ) = 8
    AND EXISTS (
        SELECT 1 FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(N'[shopease].[products]')
          AND c.name = N'id' AND t.name = N'int'
          AND c.is_nullable = 0 AND c.is_identity = 1
    )
    AND EXISTS (
        SELECT 1 FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(N'[shopease].[products]')
          AND c.name = N'name' AND t.name = N'nvarchar'
          AND c.max_length = 200 AND c.is_nullable = 0
    )
    AND EXISTS (
        SELECT 1 FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(N'[shopease].[products]')
          AND c.name = N'description' AND t.name = N'nvarchar'
          AND c.max_length = 2000 AND c.is_nullable = 1
    )
    AND EXISTS (
        SELECT 1 FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(N'[shopease].[products]')
          AND c.name = N'price' AND t.name = N'decimal'
          AND c.precision = 19 AND c.scale = 4 AND c.is_nullable = 0
    )
    AND EXISTS (
        SELECT 1 FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(N'[shopease].[products]')
          AND c.name = N'stock_quantity' AND t.name = N'int'
          AND c.is_nullable = 0
    )
    AND EXISTS (
        SELECT 1 FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(N'[shopease].[products]')
          AND c.name = N'category' AND t.name = N'nvarchar'
          AND c.max_length = 200 AND c.is_nullable = 0
          AND c.collation_name = N'Latin1_General_100_CI_AS'
    )
    AND EXISTS (
        SELECT 1 FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(N'[shopease].[products]')
          AND c.name = N'status' AND t.name = N'nvarchar'
          AND c.max_length = 16 AND c.is_nullable = 0
    )
    AND EXISTS (
        SELECT 1 FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(N'[shopease].[products]')
          AND c.name = N'created_at' AND t.name = N'datetimeoffset'
          AND c.is_nullable = 0
    )
    AND EXISTS (
        SELECT 1
        FROM sys.default_constraints AS d
        JOIN sys.columns AS c
          ON c.object_id = d.parent_object_id
         AND c.column_id = d.parent_column_id
        WHERE d.parent_object_id = OBJECT_ID(N'[shopease].[products]')
          AND c.name = N'created_at'
          AND d.name = N'DF_products_created_at'
          AND UPPER(d.definition) LIKE N'%SYSUTCDATETIME%'
    )
    AND EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE [object_id] = OBJECT_ID(N'[shopease].[products]')
          AND [name] = N'PK_products'
          AND [is_primary_key] = 1 AND [type] = 1
    )
    AND EXISTS (
        SELECT 1
        FROM sys.indexes AS i
        JOIN sys.index_columns AS ic
          ON ic.object_id = i.object_id AND ic.index_id = i.index_id
        JOIN sys.columns AS c
          ON c.object_id = ic.object_id AND c.column_id = ic.column_id
        WHERE i.object_id = OBJECT_ID(N'[shopease].[products]')
          AND i.name = N'PK_products'
          AND ic.key_ordinal = 1 AND c.name = N'id'
    )
    AND EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE [object_id] = OBJECT_ID(N'[shopease].[products]')
          AND [name] = N'IX_products_category_id'
          AND [type] = 2 AND [is_disabled] = 0
    )
    AND 2 = (
        SELECT COUNT(*)
        FROM sys.index_columns AS ic
        JOIN sys.indexes AS i
          ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        WHERE ic.object_id = OBJECT_ID(N'[shopease].[products]')
          AND i.name = N'IX_products_category_id'
          AND ic.is_included_column = 0
    )
    AND EXISTS (
        SELECT 1
        FROM sys.index_columns AS ic
        JOIN sys.indexes AS i
          ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        JOIN sys.columns AS c
          ON c.object_id = ic.object_id AND c.column_id = ic.column_id
        WHERE ic.object_id = OBJECT_ID(N'[shopease].[products]')
          AND i.name = N'IX_products_category_id'
          AND ic.key_ordinal = 1 AND c.name = N'category'
    )
    AND EXISTS (
        SELECT 1
        FROM sys.index_columns AS ic
        JOIN sys.indexes AS i
          ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        JOIN sys.columns AS c
          ON c.object_id = ic.object_id AND c.column_id = ic.column_id
        WHERE ic.object_id = OBJECT_ID(N'[shopease].[products]')
          AND i.name = N'IX_products_category_id'
          AND ic.key_ordinal = 2 AND c.name = N'id'
    )
    AND EXISTS (
        SELECT 1 FROM sys.check_constraints
        WHERE [parent_object_id] = OBJECT_ID(N'[shopease].[products]')
          AND [name] = N'CK_products_price_positive'
          AND [is_disabled] = 0 AND [is_not_trusted] = 0
          AND UPPER(REPLACE(REPLACE(REPLACE(REPLACE(
              [definition], N'[', N''), N']', N''), N'(', N''), N')', N''))
              LIKE N'%PRICE>0%'
    )
    AND EXISTS (
        SELECT 1 FROM sys.check_constraints
        WHERE [parent_object_id] = OBJECT_ID(N'[shopease].[products]')
          AND [name] = N'CK_products_stock_nonnegative'
          AND [is_disabled] = 0 AND [is_not_trusted] = 0
          AND UPPER(REPLACE(REPLACE(REPLACE(REPLACE(
              [definition], N'[', N''), N']', N''), N'(', N''), N')', N''))
              LIKE N'%STOCK_QUANTITY>=0%'
    )
    AND EXISTS (
        SELECT 1 FROM sys.check_constraints
        WHERE [parent_object_id] = OBJECT_ID(N'[shopease].[products]')
          AND [name] = N'CK_products_status'
          AND [is_disabled] = 0 AND [is_not_trusted] = 0
          AND (
              UPPER(REPLACE(REPLACE(REPLACE(REPLACE(
                  [definition], N'[', N''), N']', N''), N'(', N''), N')', N''))
                  LIKE N'%STATUS=N''ACTIVE''ORSTATUS=N''INACTIVE''%'
              OR UPPER(REPLACE(REPLACE(REPLACE(REPLACE(
                  [definition], N'[', N''), N']', N''), N'(', N''), N')', N''))
                  LIKE N'%STATUSINN''ACTIVE'',N''INACTIVE''%'
          )
    )
    THEN 1 ELSE 0 END;
"""
