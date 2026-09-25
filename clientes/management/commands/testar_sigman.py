import json
import os
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from clientes.integrations.sigman import SigmanAPIError, SigmanClient


class Command(BaseCommand):
    help = (
        "Testa a integração SIGMAN em modo SOMENTE LEITURA. "
        "Não cria, renova, edita ou salva clientes no banco."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            default=os.getenv("SIGMAN_API_URL", SigmanClient.DEFAULT_URL),
            help=f"URL base da API (padrão: {SigmanClient.DEFAULT_URL})",
        )
        parser.add_argument(
            "--api-key",
            default=os.getenv("SIGMAN_API_KEY", ""),
            help="API key SIGMAN. Prefira SIGMAN_API_KEY no ambiente para não gravar no histórico do terminal.",
        )
        parser.add_argument(
            "--token",
            default=os.getenv("SIGMAN_PAINEL_TOKEN", ""),
            help="Token do painel. Prefira SIGMAN_PAINEL_TOKEN no ambiente para não gravar no histórico do terminal.",
        )
        parser.add_argument("--usuario", default="", help="Filtra por usuário/login IPTV.")
        parser.add_argument("--pagina", type=int, default=1, help="Página a consultar.")
        parser.add_argument("--limite", type=int, default=20, help="Quantidade máxima a exibir no terminal.")
        parser.add_argument(
            "--per-page",
            type=int,
            default=100,
            dest="per_page",
            help="Quantidade solicitada à API por página.",
        )
        parser.add_argument(
            "--mostrar-senhas",
            action="store_true",
            help="Mostra as senhas completas no terminal. Sem esta opção, as senhas ficam mascaradas.",
        )
        parser.add_argument(
            "--raw",
            action="store_true",
            help="Mostra também o JSON bruto retornado pela API (pode conter dados sensíveis).",
        )
        parser.add_argument(
            "--playlist",
            action="store_true",
            help="Se --usuario for informado, consulta também GET /playlist para esse usuário.",
        )

    def handle(self, *args, **options):
        api_key = options["api_key"]
        token = options["token"]

        if not api_key:
            raise CommandError(
                "Falta a API key. Defina SIGMAN_API_KEY ou use --api-key. "
                "A documentação SIGMAN exige x-api-key + x-painel-token."
            )
        if not token:
            raise CommandError(
                "Falta o token do painel. Defina SIGMAN_PAINEL_TOKEN ou use --token."
            )

        try:
            client = SigmanClient(
                base_url=options["url"],
                api_key=api_key,
                painel_token=token,
            )
        except SigmanAPIError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.WARNING("\nSIGMAN | TESTE SOMENTE LEITURA"))
        self.stdout.write(f"API: {client.base_url}")
        self.stdout.write("Nenhum dado será salvo no banco e nenhuma ação de escrita será chamada.\n")

        try:
            me = client.me()
            self.stdout.write(self.style.SUCCESS("[OK] Autenticação aceita em GET /me"))
            if options["raw"]:
                self._print_raw("/me", me)

            payload = client.users(
                page=max(options["pagina"], 1),
                per_page=max(1, min(options["per_page"], 500)),
                username=options["usuario"],
                todos=True,
            )
            items = client.extract_items(payload)
            self.stdout.write(self.style.SUCCESS(f"[OK] GET /users retornou {len(items)} registro(s) nesta resposta.\n"))

            if options["raw"]:
                self._print_raw("/users", payload)

            if not items:
                self.stdout.write(self.style.WARNING(
                    "Nenhum usuário foi encontrado. Se a API respondeu sucesso, rode com --raw para vermos o formato real do retorno."
                ))
            else:
                self._print_users(
                    items[: max(options["limite"], 1)],
                    mostrar_senhas=options["mostrar_senhas"],
                )

            if options["playlist"]:
                username = options["usuario"].strip()
                if not username:
                    self.stdout.write(self.style.WARNING("\n--playlist exige também --usuario LOGIN_IPTV."))
                else:
                    playlist = client.playlist(username)
                    self.stdout.write(self.style.SUCCESS(f"\n[OK] GET /playlist para {username}"))
                    # Playlist pode trazer credenciais/URL; não imprime bruto sem --raw.
                    if options["raw"]:
                        self._print_raw("/playlist", playlist)
                    else:
                        self.stdout.write("Use --raw se quiser inspecionar a estrutura retornada pela playlist.")

        except SigmanAPIError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("\nTeste concluído. Nenhum registro local foi alterado."))

    def _print_users(self, items, mostrar_senhas=False):
        rows = []
        for item in items:
            u = SigmanClient.normalize_user(item)
            senha = str(u.get("password") or "")
            if senha and not mostrar_senhas:
                senha = self._mask(senha)

            rows.append([
                self._clean(u.get("name")),
                self._clean(u.get("username")),
                self._clean(senha),
                self._clean(u.get("package")),
                self._format_expiry(u.get("expiry")),
                self._clean(u.get("status")),
                self._clean(u.get("connections")),
                self._clean(u.get("server")),
            ])

        headers = ["Nome", "Usuário", "Senha", "Plano", "Vencimento", "Status", "Telas", "Servidor"]
        widths = []
        for col in range(len(headers)):
            width = len(headers[col])
            for row in rows:
                width = max(width, len(str(row[col])))
            widths.append(min(width, [24, 22, 18, 28, 20, 12, 7, 18][col]))

        def line(values):
            out = []
            for idx, value in enumerate(values):
                text = str(value)
                if len(text) > widths[idx]:
                    text = text[: max(widths[idx] - 1, 1)] + "…"
                out.append(text.ljust(widths[idx]))
            return " | ".join(out)

        self.stdout.write(line(headers))
        self.stdout.write("-+-".join("-" * w for w in widths))
        for row in rows:
            self.stdout.write(line(row))

    def _print_raw(self, title, payload):
        self.stdout.write(self.style.WARNING(f"\nJSON bruto {title}:"))
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    @staticmethod
    def _mask(value):
        value = str(value or "")
        if len(value) <= 4:
            return "*" * len(value)
        return value[:2] + ("*" * max(len(value) - 4, 4)) + value[-2:]

    @staticmethod
    def _clean(value):
        if value is None:
            return ""
        return str(value).replace("\n", " ").strip()

    @staticmethod
    def _format_expiry(value):
        value = str(value or "").strip()
        if not value:
            return ""
        normal = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normal)
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return value
