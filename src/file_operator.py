import aiofiles
from pathlib import Path


class FileOperator:
    def __init__(self, filepath: str):
        self.filepath = filepath

    async def read(self) -> str | None:
        """
        Lê o conteúdo de um arquivo.
        """
        try:
            async with aiofiles.open(self.filepath, 'r', encoding='utf-8') as f:
                content_str = await f.read()
                if content_str.strip():
                    return content_str
                else:
                    return None
        except FileNotFoundError:
            print(f"Arquivo {self.filepath} não existe")
            return None
        except PermissionError:
            print(f"Erro: sem permissão para ler o arquivo {self.filepath}")
            return None
        except Exception as e:
            print(f"Erro ao ler o arquivo {self.filepath}: {e}")
            return None

    async def write(self, content: str) -> bool:
        """
        Escreve conteúdo em um arquivo.
        """
        try:
            Path(self.filepath).parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(self.filepath, 'w', encoding='utf-8') as f:
                await f.write(content)
            return True

        except PermissionError:
            print(f"Erro: sem permissão para gravar o arquivo {self.filepath}")
            return False
        except Exception as e:
            print(f"Erro ao gravar o arquivo {self.filepath}: {e}")
            return False
