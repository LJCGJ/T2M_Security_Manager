#pragma once
#include <iostream>
#include <string>

using namespace System;
using namespace System::ComponentModel;
using namespace System::Collections;
using namespace System::Windows::Forms;
using namespace System::Data;
using namespace System::Drawing;
using namespace System::Diagnostics;
using namespace System::IO;
using namespace System::Collections::Generic;
using namespace System::Text;
using namespace System::Security::Cryptography;

// Referencias de assembly necessarias:
//  - System.Security.dll      -> ProtectedData / DPAPI (cifra chaves e token)
//  - Microsoft.VisualBasic.dll -> InputBox (usado no botao MCP ao vivo)
#using <System.Security.dll>
#using <Microsoft.VisualBasic.dll>

namespace T2MSecurityManager {

	public ref class MyForm : public System::Windows::Forms::Form
	{
	public:
		MyForm(void)
		{
			InitializeComponent();

			// --- BOTAO GERAR IA ---
			this->btnGerarIA = (gcnew System::Windows::Forms::Button());
			this->btnGerarIA->Name = L"btnGerarIA";
			this->btnGerarIA->Text = L"✨ T2M Copilot (IA)";
			this->btnGerarIA->Location = System::Drawing::Point(20, 660);
			this->btnGerarIA->Size = System::Drawing::Size(200, 35);
			this->btnGerarIA->BackColor = System::Drawing::Color::Indigo;
			this->btnGerarIA->ForeColor = System::Drawing::Color::White;
			this->btnGerarIA->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnGerarIA->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9, System::Drawing::FontStyle::Bold));
			this->btnGerarIA->Click += gcnew System::EventHandler(this, &MyForm::btnGerarIA_Click);
			this->Controls->Add(this->btnGerarIA);

			scriptPaths = gcnew Dictionary<String^, String^>();

			// Logo (runtime) + icone unificado para todas as janelas
			try {
				if (File::Exists(CaminhoApp("T2M_logo-03.png")))
					this->picLogo->Image = System::Drawing::Image::FromFile(CaminhoApp("T2M_logo-03.png"));
			}
			catch (...) {}
			CarregarIcone();

			CarregarConfiguracao();
			CarregarScriptsIA();
		}

	protected:
		~MyForm()
		{
			if (appIcon != nullptr) { delete appIcon; appIcon = nullptr; }
			if (components) delete components;
		}

	private:
		Dictionary<String^, String^>^ scriptPaths;
		Process^ pythonProcess;
		System::Drawing::Icon^ appIcon;

		// --- Variaveis do Chat Copilot ---
		Form^ formIA;
		RichTextBox^ rtbChat;
		TextBox^ txtChatInput;
		Button^ btnSendChat;
		Button^ btnTemaChat;     // alterna tema claro/escuro da janela do chat
		bool temaEscuro;         // estado atual do tema
		Button^ btnMapearSite;
		Button^ btnSaveScript;
		Button^ btnExportarRelatorio;  // exporta a conversa como relatorio HTML
		ComboBox^ comboModeloChat;

		// Botoes/controles de modo (toggle): so um ativo por vez.
		Button^ btnAutomacao;    // Botao "Automacao MCP" que abre menu (Tela/API/Banco)
		System::Windows::Forms::ContextMenuStrip^ menuAutomacao;  // menu com as 3 opcoes
		Button^ btnChatDom;      // Modo Scan DOM (varredura estatica)
		Button^ btnChatConversa; // Modo Chat (so conversa, padrao)
		Label^ lblChatStatus;    // Indicador "processando..."
		Label^ lblIndicadorIA;   // Mostra qual IA a chave selecionada usa (Claude/Gemini/OpenAI)

		// Modo ativo do chat: 0 = Chat (so conversa), 1 = DOM, 2 = Automacao (dropdown).
		// So um modo fica ligado por vez; o controle ligado fica em destaque.
		int modoAtivo;
		int tipoAutomacao;       // quando modoAtivo==2: 0=Tela, 1=API, 2=Banco

		// Dados da conexao de banco (coletados no formulario; senha cifrada com DPAPI).
		// Por enquanto so armazenados na sessao; a conexao real via MCP vem depois.
		String^ dbTipo;          // PostgreSQL, MySQL, SQLite, MariaDB...
		String^ dbHost;
		String^ dbPorta;
		String^ dbNome;
		String^ dbUsuario;
		String^ dbSenhaCifrada;  // senha protegida com DPAPI
		bool dbSomenteLeitura;
		bool dbConfigurado;      // true quando o usuario preencheu a conexao

		// Dados da requisicao de API (coletados no formulario).
		String^ apiMetodo;       // GET, POST, PUT, DELETE...
		String^ apiUrl;
		String^ apiHeaders;      // texto (uma linha por header: Nome: valor)
		String^ apiBody;         // corpo (JSON como texto)
		bool apiConfigurado;

		// Execucao NAO-BLOQUEANTE: o Python roda numa thread separada via BackgroundWorker,
		// para a janela nao congelar durante o chat ou o MCP ao vivo.
		System::ComponentModel::BackgroundWorker^ workerChat;
		int modoWorker;          // 0 = chat normal, 1 = scan DOM, 2 = MCP ao vivo
		String^ payloadWorker;   // texto que sera enviado ao Python (montado antes de rodar)

		System::Windows::Forms::PictureBox^ picLogo;
		System::Windows::Forms::ListBox^ lstScripts;
		System::Windows::Forms::Button^ btnAdd;
		System::Windows::Forms::Button^ btnRemove;
		System::Windows::Forms::Button^ btnAbrirPasta;
		System::Windows::Forms::RichTextBox^ txtOutput;
		System::Windows::Forms::Label^ lblUrl;
		System::Windows::Forms::TextBox^ txtUrl;
		System::Windows::Forms::Label^ lblToken;
		System::Windows::Forms::TextBox^ txtToken;
		System::Windows::Forms::Button^ btnLoginAuto;
		System::Windows::Forms::CheckBox^ chkHabilitarLogin;
		System::Windows::Forms::Button^ btnGerarIA;
		System::Windows::Forms::CheckBox^ chkSalvar;
		System::Windows::Forms::Button^ btnStart;
		System::Windows::Forms::Button^ btnStop;
		System::Windows::Forms::Button^ btnExport;
		System::ComponentModel::Container^ components;

		// P/Invoke para liberar handle de icone gerado a partir de bitmap
		[System::Runtime::InteropServices::DllImport("user32.dll", SetLastError = true)]
			static bool DestroyIcon(System::IntPtr handle);

		// =====================================================================
		// --- HELPERS DE CAMINHO, ICONE E CRIPTOGRAFIA ---
		// =====================================================================
	private: String^ CaminhoApp(String^ arquivo) {
		return Path::Combine(Application::StartupPath, arquivo);
	}

		   // Nome completo da conta do Windows (ex.: "LeonardoJoseCordeiro").
	private: String^ NomeUsuarioWindows() {
		String^ nome = Environment::UserName;
		if (String::IsNullOrWhiteSpace(nome)) return L"Operador";
		return nome->Trim();
	}

		   // Primeiro nome "amigavel" para a saudacao. Tenta separar nomes grudados em
		   // CamelCase (LeonardoJoseCordeiro -> Leonardo) ou por espaco/ponto.
	private: String^ PrimeiroNomeUsuario() {
		String^ nome = NomeUsuarioWindows();
		// separadores comuns
		array<Char>^ seps = { ' ', '.', '_', '-' };
		array<String^>^ partes = nome->Split(seps, StringSplitOptions::RemoveEmptyEntries);
		if (partes->Length > 0 && partes[0]->Length > 1) nome = partes[0];

		// Se ainda estiver "grudado" em CamelCase (ex.: LeonardoJose), corta no 2o maiusculo
		if (nome->Length > 3) {
			for (int i = 1; i < nome->Length; i++) {
				if (System::Char::IsUpper(nome[i])) {
					nome = nome->Substring(0, i);
					break;
				}
			}
		}
		// Capitaliza a inicial, deixa o resto como esta
		if (nome->Length >= 1)
			nome = System::Char::ToUpper(nome[0]) + nome->Substring(1);
		return nome;
	}

	private: void CarregarIcone() {
		try {
			String^ ico = CaminhoApp("icon2.ico");
			if (File::Exists(ico)) {
				appIcon = gcnew System::Drawing::Icon(ico); // caminho ideal
			}
			else if (File::Exists(CaminhoApp("T2M_logo-03.png"))) {
				System::Drawing::Bitmap^ bmp = gcnew System::Drawing::Bitmap(CaminhoApp("T2M_logo-03.png"));
				System::IntPtr h = bmp->GetHicon();
				try {
					appIcon = gcnew System::Drawing::Icon(System::Drawing::Icon::FromHandle(h), bmp->Size);
				}
				finally {
					DestroyIcon(h); // evita vazamento de handle GDI
					delete bmp;
				}
			}
			if (appIcon != nullptr) {
				this->Icon = appIcon;
				this->ShowIcon = true;
			}
		}
		catch (...) {}
	}

	private: void AplicarIcone(Form^ f) {
		if (f != nullptr && appIcon != nullptr) f->Icon = appIcon;
	}

	private: String^ ProtegerTexto(String^ texto) {
		if (String::IsNullOrEmpty(texto)) return "";
		array<System::Byte>^ dados = System::Text::Encoding::UTF8->GetBytes(texto);
		array<System::Byte>^ cifra = ProtectedData::Protect(dados, nullptr, DataProtectionScope::CurrentUser);
		return System::Convert::ToBase64String(cifra);
	}

	private: String^ DesprotegerTexto(String^ base64) {
		if (String::IsNullOrEmpty(base64)) return "";
		try {
			array<System::Byte>^ cifra = System::Convert::FromBase64String(base64);
			array<System::Byte>^ dados = ProtectedData::Unprotect(cifra, nullptr, DataProtectionScope::CurrentUser);
			return System::Text::Encoding::UTF8->GetString(dados);
		}
		catch (...) {
			return base64; // legado em texto puro: usa como esta (sera re-cifrado no proximo save)
		}
	}

#pragma region Windows Form Designer generated code
		   void InitializeComponent(void)
		   {
			   this->picLogo = (gcnew System::Windows::Forms::PictureBox());
			   this->lstScripts = (gcnew System::Windows::Forms::ListBox());
			   this->btnAdd = (gcnew System::Windows::Forms::Button());
			   this->btnRemove = (gcnew System::Windows::Forms::Button());
			   this->btnAbrirPasta = (gcnew System::Windows::Forms::Button());
			   this->txtOutput = (gcnew System::Windows::Forms::RichTextBox());
			   this->lblUrl = (gcnew System::Windows::Forms::Label());
			   this->txtUrl = (gcnew System::Windows::Forms::TextBox());
			   this->lblToken = (gcnew System::Windows::Forms::Label());
			   this->txtToken = (gcnew System::Windows::Forms::TextBox());
			   this->btnLoginAuto = (gcnew System::Windows::Forms::Button());
			   this->chkHabilitarLogin = (gcnew System::Windows::Forms::CheckBox());
			   this->chkSalvar = (gcnew System::Windows::Forms::CheckBox());
			   this->btnStart = (gcnew System::Windows::Forms::Button());
			   this->btnStop = (gcnew System::Windows::Forms::Button());
			   this->btnExport = (gcnew System::Windows::Forms::Button());
			   (cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->picLogo))->BeginInit();
			   this->SuspendLayout();

			   this->picLogo->BackColor = System::Drawing::Color::Transparent;
			   this->picLogo->Location = System::Drawing::Point(20, 15);
			   this->picLogo->Name = L"picLogo";
			   this->picLogo->Size = System::Drawing::Size(200, 60);
			   this->picLogo->SizeMode = System::Windows::Forms::PictureBoxSizeMode::Zoom;
			   this->picLogo->TabIndex = 0;
			   this->picLogo->TabStop = false;

			   this->lstScripts->Font = (gcnew System::Drawing::Font(L"Segoe UI", 10));
			   this->lstScripts->ItemHeight = 17;
			   this->lstScripts->Location = System::Drawing::Point(20, 140);
			   this->lstScripts->Name = L"lstScripts";
			   this->lstScripts->Size = System::Drawing::Size(200, 514);
			   this->lstScripts->TabIndex = 1;

			   this->btnAdd->BackColor = System::Drawing::Color::LightGreen;
			   this->btnAdd->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			   this->btnAdd->Location = System::Drawing::Point(20, 90);
			   this->btnAdd->Name = L"btnAdd";
			   this->btnAdd->Size = System::Drawing::Size(80, 35);
			   this->btnAdd->TabIndex = 2;
			   this->btnAdd->Text = L"➕ Add";
			   this->btnAdd->UseVisualStyleBackColor = false;
			   this->btnAdd->Click += gcnew System::EventHandler(this, &MyForm::btnAdd_Click);

			   this->btnRemove->BackColor = System::Drawing::Color::LightCoral;
			   this->btnRemove->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			   this->btnRemove->Location = System::Drawing::Point(105, 90);
			   this->btnRemove->Name = L"btnRemove";
			   this->btnRemove->Size = System::Drawing::Size(75, 35);
			   this->btnRemove->TabIndex = 3;
			   this->btnRemove->Text = L"🗑 Remover";
			   this->btnRemove->UseVisualStyleBackColor = false;
			   this->btnRemove->Click += gcnew System::EventHandler(this, &MyForm::btnRemove_Click);

			   this->btnAbrirPasta->BackColor = System::Drawing::Color::LightSkyBlue;
			   this->btnAbrirPasta->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			   this->btnAbrirPasta->Location = System::Drawing::Point(185, 90);
			   this->btnAbrirPasta->Name = L"btnAbrirPasta";
			   this->btnAbrirPasta->Size = System::Drawing::Size(35, 35);
			   this->btnAbrirPasta->TabIndex = 4;
			   this->btnAbrirPasta->Text = L"📂";
			   this->btnAbrirPasta->UseVisualStyleBackColor = false;
			   this->btnAbrirPasta->Click += gcnew System::EventHandler(this, &MyForm::btnAbrirPasta_Click);

			   this->txtOutput->BackColor = System::Drawing::Color::FromArgb(static_cast<System::Int32>(static_cast<System::Byte>(30)), static_cast<System::Int32>(static_cast<System::Byte>(30)),
				   static_cast<System::Int32>(static_cast<System::Byte>(30)));
			   this->txtOutput->Font = (gcnew System::Drawing::Font(L"Consolas", 10));
			   this->txtOutput->ForeColor = System::Drawing::Color::LimeGreen;
			   this->txtOutput->Location = System::Drawing::Point(240, 90);
			   this->txtOutput->Name = L"txtOutput";
			   this->txtOutput->ReadOnly = true;
			   this->txtOutput->Size = System::Drawing::Size(660, 360);
			   this->txtOutput->TabIndex = 5;
			   this->txtOutput->Text = L"";

			   this->lblUrl->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9, System::Drawing::FontStyle::Bold));
			   this->lblUrl->ForeColor = System::Drawing::Color::DarkRed;
			   this->lblUrl->Location = System::Drawing::Point(240, 460);
			   this->lblUrl->Name = L"lblUrl";
			   this->lblUrl->Size = System::Drawing::Size(100, 20);
			   this->lblUrl->TabIndex = 6;
			   this->lblUrl->Text = L"URL Alvo:";

			   this->txtUrl->Font = (gcnew System::Drawing::Font(L"Segoe UI", 10));
			   this->txtUrl->Location = System::Drawing::Point(240, 480);
			   this->txtUrl->Name = L"txtUrl";
			   this->txtUrl->Size = System::Drawing::Size(660, 25);
			   this->txtUrl->TabIndex = 7;

			   this->lblToken->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9, System::Drawing::FontStyle::Bold));
			   this->lblToken->ForeColor = System::Drawing::Color::DarkBlue;
			   this->lblToken->Location = System::Drawing::Point(240, 515);
			   this->lblToken->Name = L"lblToken";
			   this->lblToken->Size = System::Drawing::Size(100, 20);
			   this->lblToken->TabIndex = 8;
			   this->lblToken->Text = L"Token JWT:";

			   this->txtToken->Font = (gcnew System::Drawing::Font(L"Segoe UI", 10));
			   this->txtToken->Location = System::Drawing::Point(240, 535);
			   this->txtToken->Name = L"txtToken";
			   this->txtToken->Size = System::Drawing::Size(660, 25);
			   this->txtToken->UseSystemPasswordChar = true; // nao expoe o JWT na tela
			   this->txtToken->TabIndex = 11;

			   this->btnLoginAuto->BackColor = System::Drawing::Color::SteelBlue;
			   this->btnLoginAuto->Enabled = false;
			   this->btnLoginAuto->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			   this->btnLoginAuto->Font = (gcnew System::Drawing::Font(L"Segoe UI", 8, System::Drawing::FontStyle::Bold));
			   this->btnLoginAuto->Location = System::Drawing::Point(740, 510);
			   this->btnLoginAuto->Name = L"btnLoginAuto";
			   this->btnLoginAuto->Size = System::Drawing::Size(160, 25);
			   this->btnLoginAuto->TabIndex = 10;
			   this->btnLoginAuto->Text = L"🔑 Login Automatico";
			   this->btnLoginAuto->UseVisualStyleBackColor = false;
			   this->btnLoginAuto->Click += gcnew System::EventHandler(this, &MyForm::btnLoginAuto_Click);

			   this->chkHabilitarLogin->Font = (gcnew System::Drawing::Font(L"Segoe UI", 8));
			   this->chkHabilitarLogin->Location = System::Drawing::Point(660, 513);
			   this->chkHabilitarLogin->Name = L"chkHabilitarLogin";
			   this->chkHabilitarLogin->Size = System::Drawing::Size(80, 20);
			   this->chkHabilitarLogin->TabIndex = 9;
			   this->chkHabilitarLogin->Text = L"Ativar";
			   this->chkHabilitarLogin->CheckedChanged += gcnew System::EventHandler(this, &MyForm::chkHabilitarLogin_CheckedChanged);

			   this->chkSalvar->Checked = true;
			   this->chkSalvar->CheckState = System::Windows::Forms::CheckState::Checked;
			   this->chkSalvar->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9));
			   this->chkSalvar->Location = System::Drawing::Point(240, 570);
			   this->chkSalvar->Name = L"chkSalvar";
			   this->chkSalvar->Size = System::Drawing::Size(300, 25);
			   this->chkSalvar->TabIndex = 12;
			   this->chkSalvar->Text = L"Salvar configuracoes ao sair";

			   this->btnStart->BackColor = System::Drawing::Color::YellowGreen;
			   this->btnStart->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			   this->btnStart->Location = System::Drawing::Point(240, 600);
			   this->btnStart->Name = L"btnStart";
			   this->btnStart->Size = System::Drawing::Size(180, 45);
			   this->btnStart->TabIndex = 13;
			   this->btnStart->Text = L"▶ INICIAR TESTE";
			   this->btnStart->UseVisualStyleBackColor = false;
			   this->btnStart->Click += gcnew System::EventHandler(this, &MyForm::btnStart_Click);

			   this->btnStop->BackColor = System::Drawing::Color::IndianRed;
			   this->btnStop->Enabled = false;
			   this->btnStop->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			   this->btnStop->Location = System::Drawing::Point(480, 600);
			   this->btnStop->Name = L"btnStop";
			   this->btnStop->Size = System::Drawing::Size(180, 45);
			   this->btnStop->TabIndex = 14;
			   this->btnStop->Text = L"⏹ PARAR";
			   this->btnStop->UseVisualStyleBackColor = false;
			   this->btnStop->Click += gcnew System::EventHandler(this, &MyForm::btnStop_Click);

			   this->btnExport->BackColor = System::Drawing::Color::SteelBlue;
			   this->btnExport->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			   this->btnExport->Location = System::Drawing::Point(720, 600);
			   this->btnExport->Name = L"btnExport";
			   this->btnExport->Size = System::Drawing::Size(180, 45);
			   this->btnExport->TabIndex = 15;
			   this->btnExport->Text = L"💾 Exportar Log Tecnico";
			   this->btnExport->UseVisualStyleBackColor = false;
			   this->btnExport->Click += gcnew System::EventHandler(this, &MyForm::btnExport_Click);

			   this->BackColor = System::Drawing::Color::WhiteSmoke;
			   this->ClientSize = System::Drawing::Size(924, 711);
			   this->Controls->Add(this->picLogo);
			   this->Controls->Add(this->lstScripts);
			   this->Controls->Add(this->btnAdd);
			   this->Controls->Add(this->btnRemove);
			   this->Controls->Add(this->btnAbrirPasta);
			   this->Controls->Add(this->txtOutput);
			   this->Controls->Add(this->lblUrl);
			   this->Controls->Add(this->txtUrl);
			   this->Controls->Add(this->lblToken);
			   this->Controls->Add(this->chkHabilitarLogin);
			   this->Controls->Add(this->btnLoginAuto);
			   this->Controls->Add(this->txtToken);
			   this->Controls->Add(this->chkSalvar);
			   this->Controls->Add(this->btnStart);
			   this->Controls->Add(this->btnStop);
			   this->Controls->Add(this->btnExport);
			   this->Name = L"MyForm";
			   this->StartPosition = System::Windows::Forms::FormStartPosition::CenterScreen;
			   this->Text = L"T2M Security Manager v4.0 (MCP Edition)";
			   this->FormClosing += gcnew System::Windows::Forms::FormClosingEventHandler(this, &MyForm::MyForm_FormClosing);
			   (cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->picLogo))->EndInit();
			   this->ResumeLayout(false);
			   this->PerformLayout();
		   }
#pragma endregion

		   // --- FUNCOES BASICAS DA INTERFACE ---
	private: System::Void chkHabilitarLogin_CheckedChanged(System::Object^ sender, System::EventArgs^ e) {
		if (chkHabilitarLogin->Checked) {
			btnLoginAuto->Enabled = true;
			btnLoginAuto->BackColor = System::Drawing::Color::LightBlue;
		}
		else {
			btnLoginAuto->Enabled = false;
			btnLoginAuto->BackColor = System::Drawing::Color::Silver;
		}
	}

	private: System::Void btnLoginAuto_Click(System::Object^ sender, System::EventArgs^ e) {
		String^ urlAlvo = txtUrl->Text;
		if (String::IsNullOrWhiteSpace(urlAlvo)) {
			urlAlvo = "https://sgidd.t2mlab.com/auth";
			txtUrl->Text = urlAlvo;
		}
		txtUrl->Enabled = false; txtToken->Enabled = false;
		chkHabilitarLogin->Enabled = false; btnLoginAuto->Enabled = false;
		btnLoginAuto->Text = L"⏳ Aguarde...";
		txtOutput->Clear(); txtOutput->AppendText(">>> INICIANDO LOGIN AUTOMATICO...\n");

		Process^ pLogin = gcnew Process();
		try {
			ProcessStartInfo^ psi = gcnew ProcessStartInfo();
			psi->FileName = "python";
			psi->Arguments = "-u \"" + CaminhoApp("get_token.py") + "\"";
			psi->UseShellExecute = false;
			psi->RedirectStandardInput = true;   // URL enviada por stdin
			psi->RedirectStandardOutput = true;
			psi->CreateNoWindow = true;
			psi->StandardOutputEncoding = System::Text::Encoding::UTF8;
			pLogin->StartInfo = psi;

			try { pLogin->Start(); }
			catch (System::ComponentModel::Win32Exception^) {
				txtOutput->AppendText("\n>>> ERRO: 'python' nao encontrado no PATH.\n");
				return;
			}

			array<System::Byte>^ bytes = System::Text::Encoding::UTF8->GetBytes(urlAlvo);
			pLogin->StandardInput->BaseStream->Write(bytes, 0, bytes->Length);
			pLogin->StandardInput->Close();

			// Login pode levar ate ~60s (script espera o usuario logar). Teto de 180s.
			if (!pLogin->WaitForExit(180000)) {
				try { pLogin->Kill(); }
				catch (...) {}
				txtOutput->AppendText("\n>>> Tempo esgotado no login.\n");
				return;
			}

			String^ output = pLogin->StandardOutput->ReadToEnd();
			if (output->Contains("TOKEN_ENCONTRADO_INICIO")) {
				array<String^>^ partes = output->Split(gcnew array<String^>{"TOKEN_ENCONTRADO_INICIO", "TOKEN_ENCONTRADO_FIM"}, StringSplitOptions::None);
				if (partes->Length >= 2) {
					txtToken->Text = partes[1]->Trim();
					txtOutput->AppendText("\n>>> SUCESSO! Token capturado.\n");
				}
			}
			else { txtOutput->AppendText("\n>>> AVISO: Token nao encontrado.\n"); }
		}
		catch (Exception^ ex) { MessageBox::Show(L"Erro: " + ex->Message); }
		finally {
			pLogin->Close();
			txtUrl->Enabled = true; txtToken->Enabled = true; chkHabilitarLogin->Enabled = true;
			btnLoginAuto->Enabled = true; btnLoginAuto->Text = L"🔑 Login Automatico";
		}
	}

	private: void SalvarConfiguracao() {
		if (!chkSalvar->Checked) { if (File::Exists(CaminhoApp("config.txt"))) File::Delete(CaminhoApp("config.txt")); return; }
		try {
			StreamWriter^ sw = gcnew StreamWriter(CaminhoApp("config.txt"));
			sw->WriteLine(txtUrl->Text);
			sw->WriteLine(ProtegerTexto(txtToken->Text)); // token cifrado (DPAPI)
			for each(KeyValuePair<String^, String^> pair in scriptPaths) sw->WriteLine(pair.Value);
			sw->Close();
		}
		catch (...) {}
	}

	private: void CarregarConfiguracao() {
		if (!File::Exists(CaminhoApp("config.txt"))) return;
		try {
			StreamReader^ sr = gcnew StreamReader(CaminhoApp("config.txt"));
			String^ linha = sr->ReadLine(); if (linha != nullptr) txtUrl->Text = linha;
			linha = sr->ReadLine(); if (linha != nullptr) txtToken->Text = DesprotegerTexto(linha);
			while ((linha = sr->ReadLine()) != nullptr) {
				if (File::Exists(linha)) {
					String^ nome = Path::GetFileName(linha);
					if (!scriptPaths->ContainsKey(nome)) { scriptPaths->Add(nome, linha); lstScripts->Items->Add(nome); }
				}
			}
			sr->Close(); chkSalvar->Checked = true;
		}
		catch (...) {}
	}

	private: void CarregarScriptsIA() {
		try {
			String^ pastaIA = Path::Combine(Environment::GetFolderPath(Environment::SpecialFolder::MyDocuments), "modelos de teste em IA");
			if (Directory::Exists(pastaIA)) {
				array<String^>^ arquivos = Directory::GetFiles(pastaIA, "*.py");
				for each(String ^ arquivo in arquivos) {
					String^ nome = Path::GetFileName(arquivo);
					if (!scriptPaths->ContainsKey(nome)) { scriptPaths->Add(nome, arquivo); lstScripts->Items->Add(nome); }
				}
			}
		}
		catch (...) {}
	}

	private: System::Void MyForm_FormClosing(System::Object^ sender, System::Windows::Forms::FormClosingEventArgs^ e) { SalvarConfiguracao(); }

	private: System::Void btnAdd_Click(System::Object^ sender, System::EventArgs^ e) {
		OpenFileDialog^ openFile = gcnew OpenFileDialog(); openFile->Filter = "Python Scripts (*.py)|*.py";
		if (openFile->ShowDialog() == System::Windows::Forms::DialogResult::OK) {
			String^ caminho = openFile->FileName; String^ nome = Path::GetFileName(caminho);
			if (!scriptPaths->ContainsKey(nome)) { scriptPaths->Add(nome, caminho); lstScripts->Items->Add(nome); }
		}
	}

	private: System::Void btnRemove_Click(System::Object^ sender, System::EventArgs^ e) {
		if (lstScripts->SelectedIndex != -1) { scriptPaths->Remove(lstScripts->SelectedItem->ToString()); lstScripts->Items->RemoveAt(lstScripts->SelectedIndex); }
	}

	private: System::Void btnAbrirPasta_Click(System::Object^ sender, System::EventArgs^ e) {
		String^ pastaIA = Path::Combine(Environment::GetFolderPath(Environment::SpecialFolder::MyDocuments), "modelos de teste em IA");
		if (Directory::Exists(pastaIA)) Process::Start("explorer.exe", pastaIA);
		else MessageBox::Show(L"A pasta ainda nao existe.", L"Aviso");
	}

	private: System::Void btnStart_Click(System::Object^ sender, System::EventArgs^ e) {
		if (lstScripts->SelectedIndex == -1 || txtUrl->Text->Length == 0) { MessageBox::Show(L"Preencha a URL e selecione um script!"); return; }
		String^ caminho = scriptPaths[lstScripts->SelectedItem->ToString()];

		txtOutput->Clear(); txtOutput->AppendText(">>> INICIANDO TESTE DINAMICO <<<\n");
		ProcessStartInfo^ psi = gcnew ProcessStartInfo();
		psi->FileName = "python";
		// URL vai por argv[1]; TOKEN vai por variavel de ambiente (fora da linha de comando)
		psi->Arguments = "-u \"" + caminho + "\" \"" + txtUrl->Text + "\"";
		psi->EnvironmentVariables["T2M_AUTH_TOKEN"] = txtToken->Text;
		psi->UseShellExecute = false; psi->RedirectStandardOutput = true; psi->RedirectStandardError = true;
		psi->CreateNoWindow = true; psi->StandardOutputEncoding = System::Text::Encoding::UTF8; psi->StandardErrorEncoding = System::Text::Encoding::UTF8;

		pythonProcess = gcnew Process(); pythonProcess->StartInfo = psi;
		pythonProcess->OutputDataReceived += gcnew DataReceivedEventHandler(this, &MyForm::OnDataReceived);
		pythonProcess->ErrorDataReceived += gcnew DataReceivedEventHandler(this, &MyForm::OnDataReceived);
		pythonProcess->EnableRaisingEvents = true; pythonProcess->Exited += gcnew EventHandler(this, &MyForm::OnProcessExited);

		try {
			pythonProcess->Start(); pythonProcess->BeginOutputReadLine(); pythonProcess->BeginErrorReadLine();
			btnStart->Enabled = false; btnStop->Enabled = true;
		}
		catch (System::ComponentModel::Win32Exception^) {
			MessageBox::Show(L"'python' nao encontrado no PATH. Instale o Python marcando 'Add to PATH'.", L"Erro");
			ResetButtons();
		}
		catch (Exception^ ex) { MessageBox::Show(L"Erro: " + ex->Message); ResetButtons(); }
	}

	private: void OnDataReceived(System::Object^ sender, DataReceivedEventArgs^ e) {
		if (String::IsNullOrEmpty(e->Data)) return;
		if (this->IsDisposed || !this->IsHandleCreated) return;
		try {
			this->BeginInvoke(gcnew Action<String^>(this, &MyForm::AppendLog), e->Data);
		}
		catch (System::ObjectDisposedException^) {}
		catch (System::InvalidOperationException^) {}
	}
	private: void AppendLog(String^ text) { txtOutput->AppendText(text + Environment::NewLine); txtOutput->ScrollToCaret(); }
	private: void OnProcessExited(System::Object^ sender, EventArgs^ e) {
		if (this->IsDisposed || !this->IsHandleCreated) return;
		try { this->BeginInvoke(gcnew Action(this, &MyForm::ResetButtons)); }
		catch (...) {}
	}
	private: void ResetButtons() {
		btnStart->Enabled = true; btnStop->Enabled = false; txtOutput->AppendText("\n>>> FIM.");
		if (pythonProcess != nullptr) { try { pythonProcess->Close(); } catch (...) {} pythonProcess = nullptr; }
	}
	private: System::Void btnStop_Click(System::Object^ sender, System::EventArgs^ e) { if (pythonProcess != nullptr && !pythonProcess->HasExited) { try { pythonProcess->Kill(); } catch (...) {} } }
	private: System::Void btnExport_Click(System::Object^ sender, System::EventArgs^ e) {
		if (String::IsNullOrWhiteSpace(txtOutput->Text)) {
			MessageBox::Show(L"O log tecnico esta vazio. Execute alguma operacao primeiro.", L"Aviso");
			return;
		}
		ExportarComoHtml(txtOutput->Text, L"Log Tecnico",
			L"Registro tecnico das operacoes do sistema", L"log_tecnico_T2M_");
	}

	private: void CarregarDropdownAPI(ComboBox^ combo) {
		combo->Items->Clear();
		if (File::Exists(CaminhoApp("api_keys_ia.txt"))) {
			array<String^>^ linhas = File::ReadAllLines(CaminhoApp("api_keys_ia.txt"));
			for each(String ^ linha in linhas) {
				if (!String::IsNullOrWhiteSpace(linha)) {
					String^ real = DesprotegerTexto(linha->Trim());
					if (real->Length >= 10)
						combo->Items->Add(real->Substring(0, 6) + "****************" + real->Substring(real->Length - 4));
					else
						combo->Items->Add("****");
				}
			}
		}
		if (combo->Items->Count == 0) combo->Items->Add(L" Nenhuma chave ");
		combo->Items->Add("-------------------------"); combo->Items->Add(L"+ Adicionar Nova API Key...");
		combo->SelectedIndex = 0;
	}

		   // =========================================================================
		   // --- MOTOR DE CHAT COPILOT ---
		   // =========================================================================

	private: String^ ChamarAgentePython(String^ apiKey, String^ prompt, String^ url) {
		Process^ p = gcnew Process();
		try {
			ProcessStartInfo^ psi = gcnew ProcessStartInfo();
			psi->FileName = "python";
			psi->Arguments = "-u \"" + CaminhoApp("gerador_ia.py") + "\"";
			psi->UseShellExecute = false;
			psi->RedirectStandardInput = true;   // chave + prompt via stdin (nunca em argv)
			psi->RedirectStandardOutput = true;
			psi->CreateNoWindow = true;
			psi->StandardOutputEncoding = System::Text::Encoding::UTF8;
			p->StartInfo = psi;

			try { p->Start(); }
			catch (System::ComponentModel::Win32Exception^) {
				return L"Erro: 'python' nao encontrado no PATH. Instale o Python marcando 'Add to PATH'.";
			}

			// linha 1 = chave | linha 2 = url | resto = prompt (pode ser multilinha)
			String^ payload = apiKey + "\n" + url + "\n" + prompt;
			array<System::Byte>^ bytes = System::Text::Encoding::UTF8->GetBytes(payload);
			p->StandardInput->BaseStream->Write(bytes, 0, bytes->Length);
			p->StandardInput->Close();

			if (!p->WaitForExit(120000)) { // teto de 120s: nunca congela para sempre
				try { p->Kill(); }
				catch (...) {}
				return L"Tempo esgotado (120s) aguardando a IA. Verifique a conexao ou a chave.";
			}

			String^ output = p->StandardOutput->ReadToEnd();
			int startIdx = output->IndexOf("CHAT_MSG_INICIO");
			int endIdx = output->IndexOf("CHAT_MSG_FIM");
			if (startIdx != -1 && endIdx != -1) {
				startIdx += 15;
				return output->Substring(startIdx, endIdx - startIdx)->Trim();
			}
			return L"Erro de comunicacao com a IA:\n" + output;
		}
		finally {
			p->Close();
		}
	}

		   // --- AGENTE MCP AO VIVO (Playwright) ---
	private: String^ ChamarAgenteMcp(String^ apiKey, String^ objetivo, String^ url) {
		Process^ p = gcnew Process();
		try {
			ProcessStartInfo^ psi = gcnew ProcessStartInfo();
			psi->FileName = "python";
			psi->Arguments = "-u \"" + CaminhoApp("agente_mcp.py") + "\"";
			psi->UseShellExecute = false;
			psi->RedirectStandardInput = true;
			psi->RedirectStandardOutput = true;
			psi->CreateNoWindow = true;
			psi->StandardOutputEncoding = System::Text::Encoding::UTF8;
			p->StartInfo = psi;

			try { p->Start(); }
			catch (System::ComponentModel::Win32Exception^) {
				return L"Erro: 'python' nao encontrado no PATH.";
			}

			String^ payload = apiKey + "\n" + url + "\n" + objetivo;
			array<System::Byte>^ bytes = System::Text::Encoding::UTF8->GetBytes(payload);
			p->StandardInput->BaseStream->Write(bytes, 0, bytes->Length);
			p->StandardInput->Close();

			// Loop ao vivo e lento: teto de 5 minutos
			if (!p->WaitForExit(300000)) {
				try { p->Kill(); }
				catch (...) {}
				return L"Tempo esgotado (5 min) no agente MCP.";
			}

			String^ output = p->StandardOutput->ReadToEnd();
			int i = output->IndexOf("CHAT_MSG_INICIO");
			int f = output->IndexOf("CHAT_MSG_FIM");
			if (i != -1 && f != -1) return output->Substring(i + 15, f - (i + 15))->Trim();
			return L"Erro de comunicacao com o agente:\n" + output;
		}
		finally { p->Close(); }
	}

	private: String^ ObterChaveReal() {
		int idx = comboModeloChat->SelectedIndex;
		if (idx < 0) return "";
		if (File::Exists(CaminhoApp("api_keys_ia.txt"))) {
			array<String^>^ linhas = File::ReadAllLines(CaminhoApp("api_keys_ia.txt"));
			List<String^>^ chaves = gcnew List<String^>();
			for each(String ^ linha in linhas) if (!String::IsNullOrWhiteSpace(linha)) chaves->Add(DesprotegerTexto(linha->Trim()));
			if (idx >= 0 && idx < chaves->Count) return chaves[idx];
		}
		return "";
	}

		   // Detecta qual IA uma chave usa, pelo prefixo (mesma logica do roteador Python).
		   // Retorna o nome amigavel; a cor e definida em AtualizarIndicadorIA.
	private: String^ DetectarIA(String^ chave) {
		if (String::IsNullOrWhiteSpace(chave)) return L"";
		if (chave->StartsWith("sk-ant-")) return L"Claude";
		if (chave->StartsWith("sk-")) return L"OpenAI";
		return L"Gemini";  // AIza / AQ. / outros = Gemini (padrao)
	}

		   // Atualiza o indicador visual (bolinha colorida + nome) da IA da chave selecionada.
	private: void AtualizarIndicadorIA() {
		if (lblIndicadorIA == nullptr) return;
		String^ ia = DetectarIA(ObterChaveReal());
		if (ia == L"") {
			lblIndicadorIA->Text = L"";
			return;
		}
		System::Drawing::Color cor;
		if (ia == L"Claude") cor = System::Drawing::Color::MediumPurple;
		else if (ia == L"OpenAI") cor = System::Drawing::Color::MediumSeaGreen;
		else cor = System::Drawing::Color::SteelBlue;  // Gemini
		lblIndicadorIA->ForeColor = cor;
		lblIndicadorIA->Text = L"● IA: " + ia;
	}

	private: System::Void comboModeloChat_SelectedIndexChanged(System::Object^ sender, System::EventArgs^ e) {
		if (comboModeloChat->SelectedItem != nullptr && comboModeloChat->SelectedItem->ToString() == L"+ Adicionar Nova API Key...") {
			Form^ formAdd = gcnew Form();
			formAdd->Text = L"Adicionar API Key";
			formAdd->Size = System::Drawing::Size(450, 150);
			formAdd->StartPosition = FormStartPosition::CenterParent;
			formAdd->BackColor = System::Drawing::Color::WhiteSmoke;
			AplicarIcone(formAdd);

			Label^ lbl = gcnew Label();
			lbl->Text = L"Cole sua chave completa (Gemini, Anthropic Claude ou OpenAI):";
			lbl->Location = System::Drawing::Point(20, 20);
			lbl->AutoSize = true;
			formAdd->Controls->Add(lbl);

			TextBox^ txtNovaChave = gcnew TextBox();
			txtNovaChave->Location = System::Drawing::Point(20, 45);
			txtNovaChave->Size = System::Drawing::Size(390, 25);
			txtNovaChave->UseSystemPasswordChar = true;
			formAdd->Controls->Add(txtNovaChave);

			Button^ btnSalvar = gcnew Button();
			btnSalvar->Text = L"💾 Salvar Chave";
			btnSalvar->Location = System::Drawing::Point(310, 75);
			btnSalvar->Size = System::Drawing::Size(100, 30);
			btnSalvar->BackColor = System::Drawing::Color::MediumSeaGreen;
			btnSalvar->ForeColor = System::Drawing::Color::White;
			btnSalvar->FlatStyle = FlatStyle::Flat;
			btnSalvar->DialogResult = System::Windows::Forms::DialogResult::OK;
			formAdd->Controls->Add(btnSalvar);

			if (formAdd->ShowDialog() == System::Windows::Forms::DialogResult::OK) {
				String^ novaChave = txtNovaChave->Text->Trim();
				if (novaChave != "") {
					StreamWriter^ sw = gcnew StreamWriter(CaminhoApp("api_keys_ia.txt"), true);
					sw->WriteLine(ProtegerTexto(novaChave)); // cifrada em disco (DPAPI)
					sw->Close();
					MessageBox::Show(L"Chave salva com sucesso!", L"T2M Copilot");
				}
			}
			CarregarDropdownAPI(comboModeloChat);
		}
		AtualizarIndicadorIA();  // atualiza a bolinha/nome da IA conforme a chave
	}

	private: System::Void btnRemoverChave_Click(System::Object^ sender, System::EventArgs^ e) {
		int idx = comboModeloChat->SelectedIndex;
		if (idx >= 0 && comboModeloChat->SelectedItem->ToString() != L"+ Adicionar Nova API Key..." && comboModeloChat->SelectedItem->ToString() != "-------------------------" && comboModeloChat->SelectedItem->ToString() != L" Nenhuma chave ") {
			if (MessageBox::Show(L"Tem certeza que deseja excluir esta chave?", L"Confirmar Exclusao", MessageBoxButtons::YesNo, MessageBoxIcon::Warning) == System::Windows::Forms::DialogResult::Yes) {
				if (File::Exists(CaminhoApp("api_keys_ia.txt"))) {
					array<String^>^ linhas = File::ReadAllLines(CaminhoApp("api_keys_ia.txt"));
					List<String^>^ novasLinhas = gcnew List<String^>();
					int cont = 0;
					for each(String ^ linha in linhas) {
						if (!String::IsNullOrWhiteSpace(linha)) {
							if (cont != idx) novasLinhas->Add(linha);
							cont++;
						}
					}
					File::WriteAllLines(CaminhoApp("api_keys_ia.txt"), novasLinhas->ToArray());
					CarregarDropdownAPI(comboModeloChat);
					MessageBox::Show(L"Chave excluida!", L"T2M Copilot");
				}
			}
		}
		else {
			MessageBox::Show(L"Selecione uma chave valida para excluir.", L"Aviso");
		}
	}

	private: System::Void btnGerarIA_Click(System::Object^ sender, System::EventArgs^ e) {
		if (txtUrl->Text->Trim() == "") {
			MessageBox::Show(L"Preencha a URL Alvo primeiro para a IA poder analisar o projeto!", L"Aviso");
			return;
		}

		formIA = gcnew Form();
		formIA->Text = L"T2M Copilot - Arquiteto de Automacao e Qualidade";
		formIA->Size = System::Drawing::Size(750, 640);   // botoes de acao subiram para o topo
		formIA->StartPosition = FormStartPosition::CenterParent;
		formIA->BackColor = System::Drawing::Color::WhiteSmoke;
		AplicarIcone(formIA);

		formIA->Shown += gcnew System::EventHandler(this, &MyForm::formIA_Shown);

		// ToolTip compartilhado da janela (mostra o custo/uso ao passar o mouse)
		ToolTip^ dica = gcnew ToolTip();
		dica->AutoPopDelay = 8000;
		dica->InitialDelay = 400;
		dica->ReshowDelay = 200;

		Label^ lblInfo = gcnew Label();
		lblInfo->Text = L"1. Selecione a Chave API:";
		lblInfo->Location = System::Drawing::Point(20, 20);
		lblInfo->AutoSize = true;
		formIA->Controls->Add(lblInfo);

		// Indicador da IA da chave selecionada (bolinha colorida + nome)
		lblIndicadorIA = gcnew Label();
		lblIndicadorIA->Location = System::Drawing::Point(180, 20);
		lblIndicadorIA->AutoSize = true;
		lblIndicadorIA->Font = gcnew System::Drawing::Font("Segoe UI", 8, System::Drawing::FontStyle::Bold);
		lblIndicadorIA->Text = L"";
		formIA->Controls->Add(lblIndicadorIA);
		dica->SetToolTip(lblIndicadorIA,
			L"Qual IA sera usada, detectada pelo inicio da chave:\n"
			L"sk-ant-... = Claude | sk-... = OpenAI | AIza/AQ. = Gemini");

		comboModeloChat = gcnew ComboBox();
		comboModeloChat->Location = System::Drawing::Point(20, 40);
		comboModeloChat->Size = System::Drawing::Size(260, 25);
		comboModeloChat->DropDownStyle = ComboBoxStyle::DropDownList;
		comboModeloChat->SelectedIndexChanged += gcnew System::EventHandler(this, &MyForm::comboModeloChat_SelectedIndexChanged);
		CarregarDropdownAPI(comboModeloChat);
		formIA->Controls->Add(comboModeloChat);

		Button^ btnRemoverChave = gcnew Button();
		btnRemoverChave->Text = L"🗑 Excluir";
		btnRemoverChave->Location = System::Drawing::Point(290, 39);
		btnRemoverChave->Size = System::Drawing::Size(80, 27);
		btnRemoverChave->BackColor = System::Drawing::Color::LightCoral;
		btnRemoverChave->FlatStyle = FlatStyle::Flat;
		btnRemoverChave->Click += gcnew System::EventHandler(this, &MyForm::btnRemoverChave_Click);
		formIA->Controls->Add(btnRemoverChave);

		// Botao de tema (icone + texto) - canto superior direito, alinhado com o topo
		btnTemaChat = gcnew Button();
		btnTemaChat->Location = System::Drawing::Point(600, 15);
		btnTemaChat->Size = System::Drawing::Size(110, 26);
		btnTemaChat->FlatStyle = FlatStyle::Flat;
		btnTemaChat->FlatAppearance->BorderColor = System::Drawing::Color::Silver;
		btnTemaChat->Font = gcnew System::Drawing::Font("Segoe UI", 8, System::Drawing::FontStyle::Bold);
		btnTemaChat->TextAlign = System::Drawing::ContentAlignment::MiddleCenter;
		btnTemaChat->Cursor = Cursors::Hand;
		btnTemaChat->Click += gcnew System::EventHandler(this, &MyForm::btnTemaChat_Click);
		formIA->Controls->Add(btnTemaChat);
		dica->SetToolTip(btnTemaChat, L"Alterna entre tema claro e escuro (a preferencia e lembrada).");

		// Label de status (fica ao lado dos botoes de acao; some quando ocioso)
		lblChatStatus = gcnew Label();
		lblChatStatus->Text = L"";
		lblChatStatus->Location = System::Drawing::Point(20, 452);
		lblChatStatus->Size = System::Drawing::Size(690, 18);
		lblChatStatus->Font = gcnew System::Drawing::Font("Segoe UI", 9, System::Drawing::FontStyle::Italic);
		lblChatStatus->ForeColor = System::Drawing::Color::DarkSlateBlue;
		formIA->Controls->Add(lblChatStatus);

		rtbChat = gcnew RichTextBox();
		rtbChat->Location = System::Drawing::Point(20, 78);
		rtbChat->Size = System::Drawing::Size(690, 368);
		rtbChat->ReadOnly = true;
		rtbChat->BackColor = System::Drawing::Color::White;
		rtbChat->Font = gcnew System::Drawing::Font("Segoe UI", 10);
		formIA->Controls->Add(rtbChat);

		txtChatInput = gcnew TextBox();
		txtChatInput->Location = System::Drawing::Point(20, 475);
		txtChatInput->Size = System::Drawing::Size(580, 55);
		txtChatInput->Multiline = true;
		txtChatInput->Font = gcnew System::Drawing::Font("Segoe UI", 10);
		formIA->Controls->Add(txtChatInput);

		btnSendChat = gcnew Button();
		btnSendChat->Text = L"➤ Enviar";
		btnSendChat->Location = System::Drawing::Point(610, 475);
		btnSendChat->Size = System::Drawing::Size(100, 55);
		btnSendChat->BackColor = System::Drawing::Color::MediumSeaGreen;
		btnSendChat->ForeColor = System::Drawing::Color::White;
		btnSendChat->FlatStyle = FlatStyle::Flat;
		btnSendChat->Click += gcnew System::EventHandler(this, &MyForm::btnSendChat_Click);
		formIA->Controls->Add(btnSendChat);
		dica->SetToolTip(btnSendChat, L"Envia sua mensagem ao agente (conversa em texto, custo baixo).");

		// ===== BOTOES DE MODO (toggle: so um ativo por vez) =====
		// Ficam no topo, ao lado do seletor de chave. O ativo fica em destaque.

		// --- MODO CHAT (so conversa) ---
		btnChatConversa = gcnew Button();
		btnChatConversa->Text = L"💬 Chat";
		btnChatConversa->TextAlign = System::Drawing::ContentAlignment::MiddleCenter;
		btnChatConversa->Location = System::Drawing::Point(380, 38);
		btnChatConversa->Size = System::Drawing::Size(105, 29);
		btnChatConversa->FlatStyle = FlatStyle::Flat;
		btnChatConversa->Font = gcnew System::Drawing::Font("Segoe UI", 8, System::Drawing::FontStyle::Bold);
		btnChatConversa->Click += gcnew System::EventHandler(this, &MyForm::btnModoConversa_Click);
		formIA->Controls->Add(btnChatConversa);
		dica->SetToolTip(btnChatConversa,
			L"MODO CONVERSA\n"
			L"Converse com o agente para planejar testes e automacoes.\n"
			L"Custo baixo: nao escaneia a pagina nem abre navegador.");

		// --- MODO SCAN DOM ---
		btnChatDom = gcnew Button();
		btnChatDom->Text = L"🔍 Scan DOM";
		btnChatDom->TextAlign = System::Drawing::ContentAlignment::MiddleCenter;
		btnChatDom->Location = System::Drawing::Point(490, 38);
		btnChatDom->Size = System::Drawing::Size(105, 29);
		btnChatDom->FlatStyle = FlatStyle::Flat;
		btnChatDom->Font = gcnew System::Drawing::Font("Segoe UI", 8, System::Drawing::FontStyle::Bold);
		btnChatDom->Click += gcnew System::EventHandler(this, &MyForm::btnModoDom_Click);
		formIA->Controls->Add(btnChatDom);
		dica->SetToolTip(btnChatDom,
			L"MODO SCAN DOM (varredura rapida)\n"
			L"Le a estrutura da pagina (campos, botoes, formularios) pelo HTML.\n"
			L"Rapido e BARATO. Nao abre navegador nem executa acoes.\n"
			L"Bom para dar contexto inicial da tela ao agente.");

		// --- MODO AUTOMACAO (botao + menu: Tela / API / Banco) = usa MCP ---
		// Botao com texto sempre visivel; ao clicar, abre um menu com SO as 3 opcoes reais.
		btnAutomacao = gcnew Button();
		btnAutomacao->Text = L"⚙ Automacao";
		btnAutomacao->TextAlign = System::Drawing::ContentAlignment::MiddleCenter;
		btnAutomacao->Location = System::Drawing::Point(600, 38);
		btnAutomacao->Size = System::Drawing::Size(115, 29);
		btnAutomacao->FlatStyle = FlatStyle::Flat;
		btnAutomacao->Font = gcnew System::Drawing::Font("Segoe UI", 8, System::Drawing::FontStyle::Bold);
		btnAutomacao->Click += gcnew System::EventHandler(this, &MyForm::btnAutomacao_Click);
		formIA->Controls->Add(btnAutomacao);
		dica->SetToolTip(btnAutomacao,
			L"AUTOMACAO (via MCP, navegador/execucao real)\n"
			L"Teste de Tela: descreva o teste e a IA executa passo a passo ao vivo.\n"
			L"Teste de API / Banco de Dados: em breve.\n"
			L"ATENCAO: consome MUITO MAIS tokens (~100k+ por tarefa).");

		// Menu com as 3 opcoes reais (sem placeholder)
		menuAutomacao = gcnew System::Windows::Forms::ContextMenuStrip();
		System::Windows::Forms::ToolStripMenuItem^ itTela = gcnew System::Windows::Forms::ToolStripMenuItem(L"🖥 Teste de Tela");
		System::Windows::Forms::ToolStripMenuItem^ itApi = gcnew System::Windows::Forms::ToolStripMenuItem(L"🔌 Teste de API");
		System::Windows::Forms::ToolStripMenuItem^ itBanco = gcnew System::Windows::Forms::ToolStripMenuItem(L"🗄 Banco de Dados");
		itTela->Click += gcnew System::EventHandler(this, &MyForm::menuTela_Click);
		itApi->Click += gcnew System::EventHandler(this, &MyForm::menuApi_Click);
		itBanco->Click += gcnew System::EventHandler(this, &MyForm::menuBanco_Click);
		menuAutomacao->Items->Add(itTela);
		menuAutomacao->Items->Add(itApi);
		menuAutomacao->Items->Add(itBanco);

		btnSaveScript = gcnew Button();
		btnSaveScript->Text = L"💾 Extrair e Salvar Codigo";
		btnSaveScript->Location = System::Drawing::Point(20, 545);
		btnSaveScript->Size = System::Drawing::Size(450, 40);
		btnSaveScript->BackColor = System::Drawing::Color::Indigo;
		btnSaveScript->ForeColor = System::Drawing::Color::White;
		btnSaveScript->FlatStyle = FlatStyle::Flat;
		btnSaveScript->Font = gcnew System::Drawing::Font("Segoe UI", 10, System::Drawing::FontStyle::Bold);
		btnSaveScript->Click += gcnew System::EventHandler(this, &MyForm::btnSaveScript_Click);
		formIA->Controls->Add(btnSaveScript);
		dica->SetToolTip(btnSaveScript,
			L"Extrai o ultimo bloco de codigo da conversa e salva como script (.py/.robot/.sql).");

		btnExportarRelatorio = gcnew Button();
		btnExportarRelatorio->Text = L"📄 Relatorio do Teste";
		btnExportarRelatorio->Location = System::Drawing::Point(480, 545);
		btnExportarRelatorio->Size = System::Drawing::Size(230, 40);
		btnExportarRelatorio->BackColor = System::Drawing::Color::SteelBlue;
		btnExportarRelatorio->ForeColor = System::Drawing::Color::White;
		btnExportarRelatorio->FlatStyle = FlatStyle::Flat;
		btnExportarRelatorio->Font = gcnew System::Drawing::Font("Segoe UI", 10, System::Drawing::FontStyle::Bold);
		btnExportarRelatorio->Click += gcnew System::EventHandler(this, &MyForm::btnExportarRelatorio_Click);
		formIA->Controls->Add(btnExportarRelatorio);
		dica->SetToolTip(btnExportarRelatorio,
			L"Gera um relatorio HTML da conversa/teste, para documentar e compartilhar.");

		// Configura o BackgroundWorker (execucao em thread separada = janela nao congela)
		workerChat = gcnew System::ComponentModel::BackgroundWorker();
		workerChat->DoWork += gcnew System::ComponentModel::DoWorkEventHandler(this, &MyForm::workerChat_DoWork);
		workerChat->RunWorkerCompleted += gcnew System::ComponentModel::RunWorkerCompletedEventHandler(this, &MyForm::workerChat_Completed);

		// Estado inicial: modo Chat + indicador da IA da chave atual
		modoAtivo = 0;
		tipoAutomacao = 0;
		dbConfigurado = false;
		apiConfigurado = false;
		AtualizarBotoesModo();
		AtualizarIndicadorIA();

		// Carrega a preferencia de tema salva e aplica
		temaEscuro = CarregarPreferenciaTema();
		AplicarTema(temaEscuro);

		formIA->ShowDialog();
	}

		   // ==========================================================================
		   // --- TEMA CLARO / ESCURO (janela do chat) ---
		   // ==========================================================================

	private: System::Void btnTemaChat_Click(System::Object^ sender, System::EventArgs^ e) {
		temaEscuro = !temaEscuro;
		AplicarTema(temaEscuro);
		SalvarPreferenciaTema(temaEscuro);
	}

		   // Aplica as cores do tema aos controles principais da janela do chat.
	private: void AplicarTema(bool escuro) {
		if (formIA == nullptr) return;
		System::Drawing::Color fundo, fundoCampo, texto, fundoInput;
		if (escuro) {
			fundo = System::Drawing::Color::FromArgb(32, 34, 40);
			fundoCampo = System::Drawing::Color::FromArgb(24, 26, 31);
			fundoInput = System::Drawing::Color::FromArgb(44, 47, 54);
			texto = System::Drawing::Color::Gainsboro;
			btnTemaChat->Text = L"☀ Claro";
		}
		else {
			fundo = System::Drawing::Color::WhiteSmoke;
			fundoCampo = System::Drawing::Color::White;
			fundoInput = System::Drawing::Color::White;
			texto = System::Drawing::Color::Black;
			btnTemaChat->Text = L"🌙 Escuro";
		}
		formIA->BackColor = fundo;
		if (rtbChat != nullptr) { rtbChat->BackColor = fundoCampo; rtbChat->ForeColor = texto; }
		if (txtChatInput != nullptr) { txtChatInput->BackColor = fundoInput; txtChatInput->ForeColor = texto; }
		btnTemaChat->BackColor = fundoInput;
		btnTemaChat->ForeColor = texto;
		// Percorre labels soltos (titulos) para ajustar a cor do texto
		for each(Control ^ c in formIA->Controls) {
			Label^ lbl = dynamic_cast<Label^>(c);
			if (lbl != nullptr && lbl != lblChatStatus && lbl != lblIndicadorIA) {
				lbl->ForeColor = texto;
			}
		}
	}

		   // Le a preferencia de tema do disco (arquivo simples). Retorna true = escuro.
	private: bool CarregarPreferenciaTema() {
		try {
			String^ caminho = CaminhoApp("tema.txt");
			if (File::Exists(caminho)) {
				String^ v = File::ReadAllText(caminho)->Trim();
				return v == "escuro";
			}
		}
		catch (...) {}
		return false;  // padrao: claro
	}

		   // Salva a preferencia de tema no disco.
	private: void SalvarPreferenciaTema(bool escuro) {
		try {
			File::WriteAllText(CaminhoApp("tema.txt"), escuro ? "escuro" : "claro");
		}
		catch (...) {}
	}

		   // ==========================================================================
		   // --- MODOS DO CHAT (toggle: Chat / DOM / MCP) ---
		   // ==========================================================================

		   // Aplica o destaque visual: o controle do modo ativo fica forte;
		   // os outros ficam apagados (cinza). O dropdown destaca quando modo==2.
	private: void AtualizarBotoesModo() {
		System::Drawing::Color corConversaOn = System::Drawing::Color::MediumSeaGreen;
		System::Drawing::Color corDomOn = System::Drawing::Color::SteelBlue;
		System::Drawing::Color corMcpOn = System::Drawing::Color::DarkSlateBlue;
		System::Drawing::Color corOff = System::Drawing::Color::Gainsboro;
		System::Drawing::Color txtOff = System::Drawing::Color::DimGray;

		// Reseta os botoes para "apagado"
		btnChatConversa->BackColor = corOff; btnChatConversa->ForeColor = txtOff;
		btnChatDom->BackColor = corOff; btnChatDom->ForeColor = txtOff;
		btnChatConversa->Text = L"💬 Chat";
		btnChatDom->Text = L"🔍 Scan DOM";
		// Dropdown apagado por padrao
		btnAutomacao->BackColor = corOff; btnAutomacao->ForeColor = txtOff;

		// Liga o ativo
		if (modoAtivo == 0) {
			btnChatConversa->BackColor = corConversaOn; btnChatConversa->ForeColor = System::Drawing::Color::White;
			btnChatConversa->Text = L"● 💬 Chat";
		}
		else if (modoAtivo == 1) {
			btnChatDom->BackColor = corDomOn; btnChatDom->ForeColor = System::Drawing::Color::White;
			btnChatDom->Text = L"● 🔍 Scan DOM";
		}
		else if (modoAtivo == 2) {
			// Destaque do dropdown quando a automacao esta ativa
			btnAutomacao->BackColor = corMcpOn; btnAutomacao->ForeColor = System::Drawing::Color::White;
		}

		// Atualiza a dica conforme o modo
		if (txtChatInput != nullptr) {
			if (modoAtivo == 0)
				lblChatStatus->Text = L"Modo Chat: converse para planejar testes e automacoes.";
			else if (modoAtivo == 1)
				lblChatStatus->Text = L"Modo Scan DOM: sua proxima mensagem escaneia a pagina (URL Alvo) - bom para seguranca e testes simples.";
			else {
				// Mensagem depende do tipo de automacao escolhido
				if (tipoAutomacao == 0)
					lblChatStatus->Text = L"Automacao - Teste de Tela: descreva o teste; o MCP executa ao vivo (gasta mais tokens).";
				else if (tipoAutomacao == 1)
					lblChatStatus->Text = L"Automacao - Teste de API: adicione sua API aqui no chat (metodo, URL, headers, payload).";
				else
					lblChatStatus->Text = L"Automacao - Banco de Dados: informe tipo de banco e conexao quando solicitado.";
			}
		}
	}

	private: System::Void btnModoConversa_Click(System::Object^ sender, System::EventArgs^ e) {
		if (workerChat->IsBusy) return;
		modoAtivo = 0;
		AtualizarBotoesModo();
	}
	private: System::Void btnModoDom_Click(System::Object^ sender, System::EventArgs^ e) {
		if (workerChat->IsBusy) return;
		modoAtivo = 1;
		AtualizarBotoesModo();
	}

		   // Botao Automacao: abre o menu com as 3 opcoes, logo abaixo do botao.
	private: System::Void btnAutomacao_Click(System::Object^ sender, System::EventArgs^ e) {
		if (workerChat->IsBusy) return;
		menuAutomacao->Show(btnAutomacao, System::Drawing::Point(0, btnAutomacao->Height));
	}

		   // Opcao Teste de Tela - funciona (via MCP)
	private: System::Void menuTela_Click(System::Object^ sender, System::EventArgs^ e) {
		if (workerChat->IsBusy) return;
		modoAtivo = 2; tipoAutomacao = 0;
		AtualizarBotoesModo();
	}
		   // Opcao Teste de API - em breve
	private: System::Void menuApi_Click(System::Object^ sender, System::EventArgs^ e) {
		if (workerChat->IsBusy) return;
		AbrirFormularioApi();
	}

		   // Formulario que coleta os dados da requisicao de API.
	private: void AbrirFormularioApi() {
		Form^ f = gcnew Form();
		f->Text = L"Teste de API - Montar Requisicao";
		f->Size = System::Drawing::Size(520, 520);
		f->StartPosition = FormStartPosition::CenterParent;
		f->FormBorderStyle = System::Windows::Forms::FormBorderStyle::FixedDialog;
		f->MaximizeBox = false; f->MinimizeBox = false;
		f->BackColor = System::Drawing::Color::WhiteSmoke;
		AplicarIcone(f);

		int x1 = 20, larg = 460, y = 18;

		// Metodo + URL na mesma linha
		Label^ lblMet = gcnew Label(); lblMet->Text = L"Metodo:";
		lblMet->Location = System::Drawing::Point(x1, y + 3); lblMet->AutoSize = true;
		f->Controls->Add(lblMet);
		ComboBox^ cbMet = gcnew ComboBox();
		cbMet->DropDownStyle = ComboBoxStyle::DropDownList;
		cbMet->Location = System::Drawing::Point(x1 + 60, y); cbMet->Size = System::Drawing::Size(90, 24);
		cbMet->Items->Add(L"GET"); cbMet->Items->Add(L"POST"); cbMet->Items->Add(L"PUT");
		cbMet->Items->Add(L"DELETE"); cbMet->Items->Add(L"PATCH");
		cbMet->SelectedIndex = (apiMetodo != nullptr && cbMet->Items->Contains(apiMetodo))
			? cbMet->Items->IndexOf(apiMetodo) : 0;
		f->Controls->Add(cbMet);

		// URL
		y += 36;
		Label^ lblUrl = gcnew Label(); lblUrl->Text = L"URL do endpoint:";
		lblUrl->Location = System::Drawing::Point(x1, y); lblUrl->AutoSize = true;
		f->Controls->Add(lblUrl);
		Label^ errUrl = CriarLabelErro(x1 + 130, y, 300);
		f->Controls->Add(errUrl);
		y += 20;
		TextBox^ txtApiUrl = gcnew TextBox();
		txtApiUrl->Location = System::Drawing::Point(x1, y); txtApiUrl->Size = System::Drawing::Size(larg, 24);
		txtApiUrl->Text = (apiUrl != nullptr) ? apiUrl : L"https://";
		f->Controls->Add(txtApiUrl);

		// Headers
		y += 36;
		Label^ lblHead = gcnew Label();
		lblHead->Text = L"Headers (um por linha, ex.: Authorization: Bearer xxx):";
		lblHead->Location = System::Drawing::Point(x1, y); lblHead->AutoSize = true;
		f->Controls->Add(lblHead);
		y += 20;
		TextBox^ txtApiHead = gcnew TextBox();
		txtApiHead->Location = System::Drawing::Point(x1, y); txtApiHead->Size = System::Drawing::Size(larg, 70);
		txtApiHead->Multiline = true; txtApiHead->ScrollBars = ScrollBars::Vertical;
		txtApiHead->Text = (apiHeaders != nullptr) ? apiHeaders : L"Content-Type: application/json";
		f->Controls->Add(txtApiHead);

		// Body
		y += 82;
		Label^ lblBody = gcnew Label();
		lblBody->Text = L"Body (JSON - opcional, usado em POST/PUT/PATCH):";
		lblBody->Location = System::Drawing::Point(x1, y); lblBody->AutoSize = true;
		f->Controls->Add(lblBody);
		y += 20;
		TextBox^ txtApiBody = gcnew TextBox();
		txtApiBody->Location = System::Drawing::Point(x1, y); txtApiBody->Size = System::Drawing::Size(larg, 90);
		txtApiBody->Multiline = true; txtApiBody->ScrollBars = ScrollBars::Vertical;
		txtApiBody->Font = gcnew System::Drawing::Font("Consolas", 9);
		txtApiBody->Text = (apiBody != nullptr) ? apiBody : L"";
		f->Controls->Add(txtApiBody);

		// Botoes
		y += 100;
		Button^ btnOk = gcnew Button();
		btnOk->Text = L"Salvar requisicao";
		btnOk->Location = System::Drawing::Point(x1 + 130, y); btnOk->Size = System::Drawing::Size(150, 30);
		btnOk->BackColor = System::Drawing::Color::MediumSeaGreen;
		btnOk->ForeColor = System::Drawing::Color::White; btnOk->FlatStyle = FlatStyle::Flat;
		f->Controls->Add(btnOk);

		Button^ btnCancel = gcnew Button();
		btnCancel->Text = L"Cancelar";
		btnCancel->Location = System::Drawing::Point(x1 + 290, y); btnCancel->Size = System::Drawing::Size(100, 30);
		btnCancel->FlatStyle = FlatStyle::Flat;
		f->Controls->Add(btnCancel);
		btnCancel->Click += gcnew System::EventHandler(this, &MyForm::fecharDialogo_Handler);

		// Guarda campos no Tag: 0=cbMet 1=txtApiUrl 2=txtApiHead 3=txtApiBody 4=errUrl
		cli::array<Object^>^ campos = gcnew cli::array<Object^>(5);
		campos[0] = cbMet; campos[1] = txtApiUrl; campos[2] = txtApiHead;
		campos[3] = txtApiBody; campos[4] = errUrl;
		f->Tag = campos;
		btnOk->Tag = f;
		btnOk->Click += gcnew System::EventHandler(this, &MyForm::salvarApi_Click);

		f->ShowDialog();
	}

		   // Salva a requisicao de API: valida a URL, guarda na sessao, ativa o modo.
	private: System::Void salvarApi_Click(System::Object^ sender, System::EventArgs^ e) {
		Button^ b = safe_cast<Button^>(sender);
		Form^ f = safe_cast<Form^>(b->Tag);
		cli::array<Object^>^ ctl = safe_cast<cli::array<Object^>^>(f->Tag);
		ComboBox^ cbMet = safe_cast<ComboBox^>(ctl[0]);
		TextBox^ txtApiUrl = safe_cast<TextBox^>(ctl[1]);
		TextBox^ txtApiHead = safe_cast<TextBox^>(ctl[2]);
		TextBox^ txtApiBody = safe_cast<TextBox^>(ctl[3]);
		Label^ errUrl = safe_cast<Label^>(ctl[4]);

		// Validacao: URL obrigatoria, precisa de http(s):// E ter algo depois do prefixo.
		String^ url = txtApiUrl->Text->Trim();
		bool temPrefixo = url->StartsWith("http://") || url->StartsWith("https://");
		String^ depoisPrefixo = L"";
		if (url->StartsWith("https://")) depoisPrefixo = url->Substring(8)->Trim();
		else if (url->StartsWith("http://")) depoisPrefixo = url->Substring(7)->Trim();
		if (String::IsNullOrWhiteSpace(url) || !temPrefixo || String::IsNullOrWhiteSpace(depoisPrefixo)) {
			errUrl->Text = L"⚠ Informe uma URL valida (ex.: https://api.exemplo.com/rota)";
			errUrl->Visible = true;
			txtApiUrl->BackColor = System::Drawing::Color::FromArgb(255, 245, 245);
			return;
		}
		errUrl->Visible = false;
		txtApiUrl->BackColor = System::Drawing::Color::White;

		// Aviso amigavel (nao bloqueia): metodos que costumam enviar dados sem body.
		String^ met = cbMet->Text;
		bool enviaBody = (met == "POST" || met == "PUT" || met == "PATCH");
		if (enviaBody && String::IsNullOrWhiteSpace(txtApiBody->Text)) {
			System::Windows::Forms::DialogResult r = MessageBox::Show(
				L"O metodo " + met + L" normalmente envia um corpo (body), mas ele esta vazio.\n\n"
				L"Deseja salvar mesmo assim?",
				L"Body vazio", MessageBoxButtons::YesNo, MessageBoxIcon::Question);
			if (r == System::Windows::Forms::DialogResult::No) return;  // volta para preencher
		}

		apiMetodo = cbMet->Text;
		apiUrl = url;
		apiHeaders = txtApiHead->Text->Trim();
		apiBody = txtApiBody->Text->Trim();
		apiConfigurado = true;

		modoAtivo = 2; tipoAutomacao = 1;
		AtualizarBotoesModo();
		rtbChat->SelectionColor = System::Drawing::Color::DarkSlateBlue;
		rtbChat->AppendText(L">>> Requisicao de API configurada: " + apiMetodo + L" " + apiUrl + L"\n");
		rtbChat->AppendText(L">>> Descreva no chat o que quer validar (ex.: 'verifique se retorna 200 e tem o campo id').\n\n");

		f->Close();
	}
		   // Opcao Banco de Dados - abre o formulario de conexao (interface pronta; a
		   // conexao real via MCP sera plugada depois).
	private: System::Void menuBanco_Click(System::Object^ sender, System::EventArgs^ e) {
		if (workerChat->IsBusy) return;
		AbrirFormularioConexaoBanco();
	}

		   // Formulario que coleta os dados de conexao do banco, com validacao visual.
	private: void AbrirFormularioConexaoBanco() {
		Form^ f = gcnew Form();
		f->Text = L"Conexao de Banco de Dados";
		f->Size = System::Drawing::Size(460, 520);
		f->StartPosition = FormStartPosition::CenterParent;
		f->FormBorderStyle = System::Windows::Forms::FormBorderStyle::FixedDialog;
		f->MaximizeBox = false; f->MinimizeBox = false;
		f->BackColor = System::Drawing::Color::WhiteSmoke;
		AplicarIcone(f);

		int x1 = 20, x2 = 150, larg = 260, alt = 24, y = 18, dy = 50;

		// Tipo de banco
		Label^ lblTipo = gcnew Label(); lblTipo->Text = L"Tipo de banco:";
		lblTipo->Location = System::Drawing::Point(x1, y + 3); lblTipo->AutoSize = true;
		f->Controls->Add(lblTipo);
		ComboBox^ cbTipo = gcnew ComboBox();
		cbTipo->DropDownStyle = ComboBoxStyle::DropDownList;
		cbTipo->Location = System::Drawing::Point(x2, y); cbTipo->Size = System::Drawing::Size(larg, alt);
		cbTipo->Items->Add(L"PostgreSQL"); cbTipo->Items->Add(L"MySQL");
		cbTipo->Items->Add(L"MariaDB"); cbTipo->Items->Add(L"SQLite");
		cbTipo->Items->Add(L"SQL Server");
		cbTipo->Items->Add(L"Oracle (em breve)");
		cbTipo->Items->Add(L"MongoDB (em breve)");
		cbTipo->SelectedIndex = (dbTipo != nullptr && cbTipo->Items->Contains(dbTipo))
			? cbTipo->Items->IndexOf(dbTipo) : 0;
		f->Controls->Add(cbTipo);

		// Host
		y += dy;
		Label^ lblHost = gcnew Label(); lblHost->Text = L"Host / Servidor:";
		lblHost->Location = System::Drawing::Point(x1, y + 3); lblHost->AutoSize = true;
		f->Controls->Add(lblHost);
		TextBox^ txtHost = gcnew TextBox();
		txtHost->Location = System::Drawing::Point(x2, y); txtHost->Size = System::Drawing::Size(larg, alt);
		txtHost->Text = (dbHost != nullptr) ? dbHost : L"localhost";
		f->Controls->Add(txtHost);
		Label^ errHost = CriarLabelErro(x2, y + alt + 1, larg); f->Controls->Add(errHost);

		// Porta
		y += dy;
		Label^ lblPorta = gcnew Label(); lblPorta->Text = L"Porta:";
		lblPorta->Location = System::Drawing::Point(x1, y + 3); lblPorta->AutoSize = true;
		f->Controls->Add(lblPorta);
		TextBox^ txtPorta = gcnew TextBox();
		txtPorta->Location = System::Drawing::Point(x2, y); txtPorta->Size = System::Drawing::Size(larg, alt);
		txtPorta->Text = (dbPorta != nullptr) ? dbPorta : L"5432";
		f->Controls->Add(txtPorta);

		// Nome do banco
		y += dy;
		Label^ lblNome = gcnew Label(); lblNome->Text = L"Nome do banco:";
		lblNome->Location = System::Drawing::Point(x1, y + 3); lblNome->AutoSize = true;
		f->Controls->Add(lblNome);
		TextBox^ txtNome = gcnew TextBox();
		txtNome->Location = System::Drawing::Point(x2, y); txtNome->Size = System::Drawing::Size(larg, alt);
		txtNome->Text = (dbNome != nullptr) ? dbNome : L"";
		f->Controls->Add(txtNome);
		Label^ errNome = CriarLabelErro(x2, y + alt + 1, larg); f->Controls->Add(errNome);

		// Usuario
		y += dy;
		Label^ lblUser = gcnew Label(); lblUser->Text = L"Usuario:";
		lblUser->Location = System::Drawing::Point(x1, y + 3); lblUser->AutoSize = true;
		f->Controls->Add(lblUser);
		TextBox^ txtUser = gcnew TextBox();
		txtUser->Location = System::Drawing::Point(x2, y); txtUser->Size = System::Drawing::Size(larg, alt);
		txtUser->Text = (dbUsuario != nullptr) ? dbUsuario : L"";
		f->Controls->Add(txtUser);
		Label^ errUser = CriarLabelErro(x2, y + alt + 1, larg); f->Controls->Add(errUser);

		// Senha (mascarada)
		y += dy;
		Label^ lblSenha = gcnew Label(); lblSenha->Text = L"Senha:";
		lblSenha->Location = System::Drawing::Point(x1, y + 3); lblSenha->AutoSize = true;
		f->Controls->Add(lblSenha);
		TextBox^ txtSenha = gcnew TextBox();
		txtSenha->Location = System::Drawing::Point(x2, y); txtSenha->Size = System::Drawing::Size(larg, alt);
		txtSenha->UseSystemPasswordChar = true;
		txtSenha->Text = (dbSenhaCifrada != nullptr) ? DesprotegerTexto(dbSenhaCifrada) : L"";
		f->Controls->Add(txtSenha);

		// Somente leitura
		y += dy;
		CheckBox^ chkRO = gcnew CheckBox();
		chkRO->Text = L"Somente leitura (recomendado - so consultas SELECT)";
		chkRO->Location = System::Drawing::Point(x1, y); chkRO->AutoSize = true;
		chkRO->Checked = dbConfigurado ? dbSomenteLeitura : true;
		f->Controls->Add(chkRO);

		// Aviso de seguranca
		y += 30;
		Label^ lblAviso = gcnew Label();
		lblAviso->Text = L"Dica: use um usuario de banco com privilegios minimos e, se possivel,\num ambiente de testes - evite credenciais de producao.";
		lblAviso->Location = System::Drawing::Point(x1, y); lblAviso->Size = System::Drawing::Size(410, 34);
		lblAviso->ForeColor = System::Drawing::Color::DimGray;
		lblAviso->Font = gcnew System::Drawing::Font("Segoe UI", 8);
		f->Controls->Add(lblAviso);

		// Botoes
		y += 42;
		Button^ btnOk = gcnew Button();
		btnOk->Text = L"Salvar conexao";
		btnOk->Location = System::Drawing::Point(x2, y); btnOk->Size = System::Drawing::Size(140, 30);
		btnOk->BackColor = System::Drawing::Color::MediumSeaGreen;
		btnOk->ForeColor = System::Drawing::Color::White; btnOk->FlatStyle = FlatStyle::Flat;
		f->Controls->Add(btnOk);

		Button^ btnCancel = gcnew Button();
		btnCancel->Text = L"Cancelar";
		btnCancel->Location = System::Drawing::Point(x2 + 150, y); btnCancel->Size = System::Drawing::Size(100, 30);
		btnCancel->FlatStyle = FlatStyle::Flat;
		f->Controls->Add(btnCancel);

		btnCancel->Click += gcnew System::EventHandler(this, &MyForm::fecharDialogo_Handler);

		// Guarda campos + labels de erro no Tag (para o salvar validar e mostrar erros).
		// Ordem: 0=cbTipo 1=txtHost 2=txtPorta 3=txtNome 4=txtUser 5=txtSenha 6=chkRO
		//        7=errHost 8=errNome 9=errUser
		cli::array<Object^>^ campos = gcnew cli::array<Object^>(10);
		campos[0] = cbTipo; campos[1] = txtHost; campos[2] = txtPorta;
		campos[3] = txtNome; campos[4] = txtUser; campos[5] = txtSenha;
		campos[6] = chkRO; campos[7] = errHost; campos[8] = errNome; campos[9] = errUser;
		f->Tag = campos;
		btnOk->Tag = f;
		btnOk->Click += gcnew System::EventHandler(this, &MyForm::salvarConexaoBanco_Click);

		f->ShowDialog();
	}

		   // Cria um label de erro (vermelho, pequeno) inicialmente vazio/invisivel.
	private: Label^ CriarLabelErro(int x, int y, int larg) {
		Label^ l = gcnew Label();
		l->Text = L"";
		l->Location = System::Drawing::Point(x, y);
		l->Size = System::Drawing::Size(larg, 16);
		l->ForeColor = System::Drawing::Color::Firebrick;
		l->Font = gcnew System::Drawing::Font("Segoe UI", 7.5f);
		l->Visible = false;
		return l;
	}

		   // Marca um campo com erro: borda vermelha e mostra o texto de erro embaixo.
	private: void MarcarErroCampo(TextBox^ campo, Label^ lblErro, String^ msg) {
		campo->BorderStyle = System::Windows::Forms::BorderStyle::FixedSingle;
		campo->BackColor = System::Drawing::Color::FromArgb(255, 245, 245); // rosa bem claro
		lblErro->Text = L"⚠ " + msg;
		lblErro->Visible = true;
	}

		   // Limpa o erro visual de um campo (volta ao normal).
	private: void LimparErroCampo(TextBox^ campo, Label^ lblErro) {
		campo->BorderStyle = System::Windows::Forms::BorderStyle::Fixed3D;
		campo->BackColor = System::Drawing::Color::White;
		lblErro->Text = L"";
		lblErro->Visible = false;
	}

		   // Handlers auxiliares do formulario de conexao
	private: System::Void fecharDialogo_Handler(System::Object^ sender, System::EventArgs^ e) {
		Control^ c = safe_cast<Control^>(sender);
		if (c != nullptr && c->FindForm() != nullptr) c->FindForm()->Close();
	}

		   // Monta o DSN (connection string) a partir dos dados de conexao salvos.
		   // Ex.: postgres://user:senha@host:5432/db  |  mysql://user:senha@host:3306/db
	private: String^ MontarDSN() {
		if (!dbConfigurado) return L"";
		String^ senha = String::IsNullOrEmpty(dbSenhaCifrada) ? L"" : DesprotegerTexto(dbSenhaCifrada);
		String^ esquema;
		String^ t = dbTipo;
		if (t == "PostgreSQL")      esquema = L"postgres";
		else if (t == "MySQL")      esquema = L"mysql";
		else if (t == "MariaDB")    esquema = L"mysql";     // MariaDB usa driver mysql
		else if (t == "SQL Server") esquema = L"sqlserver";
		else if (t == "SQLite")     esquema = L"sqlite";
		else                        esquema = L"postgres"; // fallback

		// SQLite e um arquivo local
		if (t == "SQLite") {
			String^ caminho = !String::IsNullOrWhiteSpace(dbNome) ? dbNome : dbHost;
			return L"sqlite://" + caminho;
		}

		String^ userInfo = dbUsuario;
		if (!String::IsNullOrEmpty(senha)) userInfo += L":" + senha;
		String^ hostPorta = dbHost;
		if (!String::IsNullOrWhiteSpace(dbPorta)) hostPorta += L":" + dbPorta;
		return esquema + L"://" + userInfo + L"@" + hostPorta + L"/" + dbNome;
	}

		   // Salva a conexao: valida por tipo (borda vermelha + texto embaixo), cifra a senha.
	private: System::Void salvarConexaoBanco_Click(System::Object^ sender, System::EventArgs^ e) {
		Button^ b = safe_cast<Button^>(sender);
		Form^ f = safe_cast<Form^>(b->Tag);
		cli::array<Object^>^ ctl = safe_cast<cli::array<Object^>^>(f->Tag);
		ComboBox^ cbTipo = safe_cast<ComboBox^>(ctl[0]);
		TextBox^ txtHost = safe_cast<TextBox^>(ctl[1]);
		TextBox^ txtPorta = safe_cast<TextBox^>(ctl[2]);
		TextBox^ txtNome = safe_cast<TextBox^>(ctl[3]);
		TextBox^ txtUser = safe_cast<TextBox^>(ctl[4]);
		TextBox^ txtSenha = safe_cast<TextBox^>(ctl[5]);
		CheckBox^ chkRO = safe_cast<CheckBox^>(ctl[6]);
		Label^ errHost = safe_cast<Label^>(ctl[7]);
		Label^ errNome = safe_cast<Label^>(ctl[8]);
		Label^ errUser = safe_cast<Label^>(ctl[9]);

		String^ tipo = cbTipo->Text;
		bool ehSQLite = (tipo == "SQLite");

		// Limpa erros anteriores
		LimparErroCampo(txtHost, errHost);
		LimparErroCampo(txtNome, errNome);
		LimparErroCampo(txtUser, errUser);

		// Validacao inteligente por tipo:
		//  - SQLite: exige so o "Nome do banco" (caminho do arquivo)
		//  - Demais: exigem Host, Usuario e Nome do banco
		bool ok = true;
		if (ehSQLite) {
			if (String::IsNullOrWhiteSpace(txtNome->Text)) {
				MarcarErroCampo(txtNome, errNome, L"Informe o caminho do arquivo .db"); ok = false;
			}
		}
		else {
			if (String::IsNullOrWhiteSpace(txtHost->Text)) {
				MarcarErroCampo(txtHost, errHost, L"Campo obrigatorio"); ok = false;
			}
			if (String::IsNullOrWhiteSpace(txtUser->Text)) {
				MarcarErroCampo(txtUser, errUser, L"Campo obrigatorio"); ok = false;
			}
			if (String::IsNullOrWhiteSpace(txtNome->Text)) {
				MarcarErroCampo(txtNome, errNome, L"Campo obrigatorio"); ok = false;
			}
		}
		if (!ok) return;  // nao salva enquanto houver campos obrigatorios vazios

		// Oracle e MongoDB ainda nao tem servidor MCP configurado: avisa mas deixa salvar.
		if (tipo->Contains("em breve")) {
			MessageBox::Show(
				tipo->Replace(" (em breve)", "") + L" ainda nao tem conexao ativa "
				L"(precisa de um servidor MCP proprio, que chega numa proxima versao).\n\n"
				L"Voce pode salvar a conexao mesmo assim - ela ficara pronta para quando o "
				L"suporte for habilitado.",
				L"Banco em breve", MessageBoxButtons::OK, MessageBoxIcon::Information);
		}

		dbTipo = tipo;
		dbHost = txtHost->Text->Trim();
		dbPorta = txtPorta->Text->Trim();
		dbNome = txtNome->Text->Trim();
		dbUsuario = txtUser->Text->Trim();
		dbSenhaCifrada = String::IsNullOrEmpty(txtSenha->Text) ? L"" : ProtegerTexto(txtSenha->Text);
		dbSomenteLeitura = chkRO->Checked;
		dbConfigurado = true;

		// Ativa o modo automacao/banco e informa no chat
		modoAtivo = 2; tipoAutomacao = 2;
		AtualizarBotoesModo();
		rtbChat->SelectionColor = System::Drawing::Color::DarkSlateBlue;
		rtbChat->AppendText(L">>> Conexao de banco configurada: " + dbTipo +
			L" @ " + (dbHost == "" ? L"(arquivo)" : dbHost) +
			(dbSomenteLeitura ? L" [somente leitura]" : L" [leitura/escrita]") + L"\n");
		rtbChat->AppendText(L">>> (A execucao real via MCP sera habilitada em breve.)\n\n");

		f->Close();
	}
		   // Aviso comum de "em breve" (API/Banco)
	private: void AvisarEmBreve(String^ oque) {
		MessageBox::Show(
			oque + L" estara disponivel em breve.\n\nPor enquanto, use o Teste de Tela "
			L"(automacao ao vivo no navegador) ou os modos Chat e Scan DOM.",
			L"Em breve", MessageBoxButtons::OK, MessageBoxIcon::Information);
	}

		   // ==========================================================================
		   // --- EXECUCAO NAO-BLOQUEANTE (BackgroundWorker) ---
		   // ==========================================================================

		   // Habilita/desabilita os controles enquanto o Python roda, e mostra status.
	private: void DefinirOcupado(bool ocupado, String^ msgStatus) {
		btnSendChat->Enabled = !ocupado;
		btnAutomacao->Enabled = !ocupado;
		btnChatDom->Enabled = !ocupado;
		btnChatConversa->Enabled = !ocupado;
		btnSaveScript->Enabled = !ocupado;
		btnExportarRelatorio->Enabled = !ocupado;
		txtChatInput->Enabled = !ocupado;
		if (ocupado)
			lblChatStatus->Text = msgStatus;
		// quando desocupa, o status e restaurado por AtualizarBotoesModo (chamado no Completed)
		formIA->Cursor = ocupado ? Cursors::WaitCursor : Cursors::Default;
	}

		   // Campos capturados na thread da UI antes de rodar o worker (evita acesso cross-thread)
	private:
		String^ workerApiKey;
		String^ workerUrl;

		// Dispara o Python em background. modo: 0=chat, 1=DOM, 2=MCP. payload ja montado.
	private: void RodarWorker(int modo, String^ payload, String^ statusMsg) {
		if (workerChat->IsBusy) return;   // ja tem algo rodando

		// Captura tudo que vem da UI AGORA (thread principal), pois o DoWork roda
		// em outra thread e nao pode tocar em controles com seguranca.
		workerApiKey = ObterChaveReal();
		workerUrl = txtUrl->Text;
		if (workerApiKey == "") { MessageBox::Show(L"Selecione a API Key!", L"Aviso"); return; }

		modoWorker = modo;
		payloadWorker = payload;
		DefinirOcupado(true, statusMsg);
		workerChat->RunWorkerAsync();
	}

		   // Roda na THREAD SEPARADA. Nao pode tocar na UI aqui; usa os valores capturados.
	private: System::Void workerChat_DoWork(System::Object^ sender, System::ComponentModel::DoWorkEventArgs^ e) {
		if (modoWorker == 2) {
			// MCP ao vivo: payloadWorker contem o objetivo do teste
			e->Result = ChamarAgenteMcp(workerApiKey, payloadWorker, workerUrl);
		}
		else {
			// Chat normal (0) ou scan DOM (1): ambos via gerador_ia.py.
			e->Result = ChamarAgentePython(workerApiKey, payloadWorker, workerUrl);
		}
	}

		   // Volta para a THREAD DA UI quando o Python termina. Aqui pode atualizar a tela.
	private: System::Void workerChat_Completed(System::Object^ sender, System::ComponentModel::RunWorkerCompletedEventArgs^ e) {
		String^ resposta = (e->Error != nullptr)
			? (L"ERRO interno: " + e->Error->Message)
			: safe_cast<String^>(e->Result);

		rtbChat->SelectionColor = (modoWorker == 2)
			? System::Drawing::Color::DarkSlateBlue
			: System::Drawing::Color::DarkGreen;
		String^ prefixo = (modoWorker == 2) ? L"T2M Copilot (MCP ao vivo):\n" : L"T2M Copilot Arquiteto:\n";
		rtbChat->AppendText(L"\n" + prefixo + resposta + L"\n\n");
		rtbChat->ScrollToCaret();

		DefinirOcupado(false, L"");
		AtualizarBotoesModo();  // restaura o destaque e o texto de status do modo ativo
	}

	private: System::Void formIA_Shown(System::Object^ sender, System::EventArgs^ e) {
		// Mensagem de abertura FIXA (instantanea, nao chama a IA, nao gasta token).
		rtbChat->SelectionColor = System::Drawing::Color::Indigo;
		rtbChat->SelectionFont = gcnew System::Drawing::Font("Segoe UI", 12, System::Drawing::FontStyle::Bold);
		rtbChat->AppendText(L"T2M Copilot\n");

		rtbChat->SelectionFont = gcnew System::Drawing::Font("Segoe UI", 10);
		rtbChat->SelectionColor = System::Drawing::Color::Black;
		rtbChat->AppendText(L"Assistente especialista em Automacao, Qualidade (QA) e Seguranca.\n\n");
		rtbChat->AppendText(L"Escolha um modo no topo (passe o mouse para ver detalhes):\n");

		rtbChat->SelectionColor = System::Drawing::Color::MediumSeaGreen;
		rtbChat->SelectionFont = gcnew System::Drawing::Font("Segoe UI", 10, System::Drawing::FontStyle::Bold);
		rtbChat->AppendText(L"   💬 Chat");
		rtbChat->SelectionColor = System::Drawing::Color::Black;
		rtbChat->SelectionFont = gcnew System::Drawing::Font("Segoe UI", 10);
		rtbChat->AppendText(L" - conversar e planejar (barato).\n");

		rtbChat->SelectionColor = System::Drawing::Color::SteelBlue;
		rtbChat->SelectionFont = gcnew System::Drawing::Font("Segoe UI", 10, System::Drawing::FontStyle::Bold);
		rtbChat->AppendText(L"   🔍 Scan DOM");
		rtbChat->SelectionColor = System::Drawing::Color::Black;
		rtbChat->SelectionFont = gcnew System::Drawing::Font("Segoe UI", 10);
		rtbChat->AppendText(L" - ler a estrutura da pagina (seguranca e testes simples).\n");

		rtbChat->SelectionColor = System::Drawing::Color::DarkSlateBlue;
		rtbChat->SelectionFont = gcnew System::Drawing::Font("Segoe UI", 10, System::Drawing::FontStyle::Bold);
		rtbChat->AppendText(L"   ⚙ Automacao");
		rtbChat->SelectionColor = System::Drawing::Color::Black;
		rtbChat->SelectionFont = gcnew System::Drawing::Font("Segoe UI", 10);
		rtbChat->AppendText(L" - executar ao vivo no navegador via MCP (Teste de Tela).\n\n");

		rtbChat->SelectionColor = System::Drawing::Color::Indigo;
		rtbChat->SelectionFont = gcnew System::Drawing::Font("Segoe UI", 10, System::Drawing::FontStyle::Bold);
		rtbChat->AppendText(L"Ola, " + PrimeiroNomeUsuario() + L"! Qual e a tarefa de hoje?\n\n");

		// Volta a fonte/cor padrao para as proximas mensagens
		rtbChat->SelectionFont = gcnew System::Drawing::Font("Segoe UI", 10);
		rtbChat->SelectionColor = System::Drawing::Color::Black;
		rtbChat->ScrollToCaret();

		// Aviso discreto se nao houver chave (nao trava, so informa)
		if (ObterChaveReal() == "") {
			rtbChat->SelectionColor = System::Drawing::Color::Firebrick;
			rtbChat->AppendText(L">>> Selecione uma chave de API acima para comecar.\n\n");
			rtbChat->SelectionColor = System::Drawing::Color::Black;
		}
	}

	private: System::Void btnSendChat_Click(System::Object^ sender, System::EventArgs^ e) {
		String^ prompt = txtChatInput->Text->Trim();
		if (prompt == "") return;
		String^ apiKey = ObterChaveReal();
		if (apiKey == "") { MessageBox::Show(L"Selecione a API Key!", L"Aviso"); return; }

		// Validacao por modo
		if (modoAtivo == 1 && String::IsNullOrWhiteSpace(txtUrl->Text)) {
			MessageBox::Show(L"Preencha a URL Alvo na tela principal para usar o Scan DOM.", L"Aviso");
			return;
		}
		if (modoAtivo == 2 && tipoAutomacao == 0 && String::IsNullOrWhiteSpace(txtUrl->Text)) {
			MessageBox::Show(L"Preencha a URL Alvo na tela principal para o Teste de Tela.", L"Aviso");
			return;
		}
		if (modoAtivo == 2 && tipoAutomacao == 2 && !dbConfigurado) {
			MessageBox::Show(L"Configure a conexao de banco primeiro (menu Automacao > Banco de Dados).", L"Aviso");
			return;
		}
		if (modoAtivo == 2 && tipoAutomacao == 1 && !apiConfigurado) {
			MessageBox::Show(L"Configure a requisicao de API primeiro (menu Automacao > Teste de API).", L"Aviso");
			return;
		}

		// Eco da mensagem do usuario
		rtbChat->SelectionColor = System::Drawing::Color::DarkBlue;
		rtbChat->AppendText(NomeUsuarioWindows() + L":\n" + prompt + L"\n\n");
		txtChatInput->Clear();

		// Decide a acao conforme o modo ativo
		if (modoAtivo == 2 && tipoAutomacao == 1) {
			// TESTE DE API: monta o JSON e envia via ferramenta HTTP do agente
			rtbChat->SelectionColor = System::Drawing::Color::DarkSlateBlue;
			rtbChat->AppendText(L">>> Testando a API (" + apiMetodo + L" " + apiUrl + L"). Aguarde...\n\n");
			RodarWorkerApi(prompt);
		}
		else if (modoAtivo == 2 && tipoAutomacao == 2) {
			// AUTOMACAO DE BANCO: monta o DSN e envia via MCP (DBHub)
			rtbChat->SelectionColor = System::Drawing::Color::DarkSlateBlue;
			rtbChat->AppendText(L">>> Consultando o banco (" + dbTipo + L") via MCP. Aguarde...\n\n");
			RodarWorkerBanco(prompt);
		}
		else if (modoAtivo == 2) {
			// AUTOMACAO DE TELA: o texto do usuario e o objetivo do teste
			rtbChat->SelectionColor = System::Drawing::Color::DarkSlateBlue;
			rtbChat->AppendText(L">>> Iniciando automacao ao vivo. Uma janela do navegador vai abrir. Aguarde...\n\n");
			RodarWorker(2, prompt, L"Automacao ao vivo em andamento (navegador aberto)...");
		}
		else if (modoAtivo == 1) {
			// Scan DOM
			rtbChat->SelectionColor = System::Drawing::Color::DimGray;
			rtbChat->AppendText(L">>> Escaneando a estrutura de " + txtUrl->Text + L"...\n\n");
			RodarWorker(1, L"--SCAN_DOM--\n" + prompt, L"Escaneando a pagina (DOM)...");
		}
		else {
			// Chat normal (so conversa)
			RodarWorker(0, prompt, L"O agente esta pensando...");
		}
	}

		   // Dispara o worker para o modo BANCO: passa o DSN via URL com marcador --DB--.
		   // O agente_mcp.py detecta o marcador e sobe o DBHub em vez do Playwright.
	private: void RodarWorkerBanco(String^ objetivo) {
		if (workerChat->IsBusy) return;
		workerApiKey = ObterChaveReal();
		if (workerApiKey == "") { MessageBox::Show(L"Selecione a API Key!", L"Aviso"); return; }
		// "URL" para o banco = --DB--<dsn>|<readonly>
		String^ dsn = MontarDSN();
		workerUrl = L"--DB--" + dsn + L"|" + (dbSomenteLeitura ? L"1" : L"0");
		modoWorker = 2;              // usa ChamarAgenteMcp (que roteia p/ agente_mcp.py)
		payloadWorker = objetivo;
		DefinirOcupado(true, L"Consultando o banco de dados...");
		workerChat->RunWorkerAsync();
	}

		   // Monta o JSON da requisicao de API a partir dos dados salvos.
		   // Converte os headers (texto "Nome: valor" por linha) em objeto JSON.
	private: String^ MontarJsonApi() {
		System::Text::StringBuilder^ sb = gcnew System::Text::StringBuilder();
		sb->Append(L"{");
		sb->Append(L"\"metodo\":\"" + EscaparJson(apiMetodo) + L"\",");
		sb->Append(L"\"url\":\"" + EscaparJson(apiUrl) + L"\",");
		// headers: transforma cada linha "Nome: valor" em par chave:valor
		sb->Append(L"\"headers\":{");
		if (!String::IsNullOrWhiteSpace(apiHeaders)) {
			array<String^>^ linhas = apiHeaders->Split('\n');
			bool primeiro = true;
			for each(String ^ linha in linhas) {
				String^ l = linha->Trim();
				int dp = l->IndexOf(':');
				if (dp > 0) {
					String^ nome = l->Substring(0, dp)->Trim();
					String^ valor = l->Substring(dp + 1)->Trim();
					if (!primeiro) sb->Append(L",");
					sb->Append(L"\"" + EscaparJson(nome) + L"\":\"" + EscaparJson(valor) + L"\"");
					primeiro = false;
				}
			}
		}
		sb->Append(L"},");
		// body como texto (o Python interpreta como JSON se possivel)
		sb->Append(L"\"body\":\"" + EscaparJson(apiBody) + L"\"");
		sb->Append(L"}");
		return sb->ToString();
	}

		   // Escapa caracteres especiais para o JSON nao quebrar.
	private: String^ EscaparJson(String^ s) {
		if (s == nullptr) return L"";
		s = s->Replace(L"\\", L"\\\\");
		s = s->Replace(L"\"", L"\\\"");
		s = s->Replace(L"\r", L"");
		s = s->Replace(L"\n", L"\\n");
		s = s->Replace(L"\t", L"\\t");
		return s;
	}

		   // Dispara o worker para o modo API: passa o JSON via URL com marcador --API--.
	private: void RodarWorkerApi(String^ objetivo) {
		if (workerChat->IsBusy) return;
		workerApiKey = ObterChaveReal();
		if (workerApiKey == "") { MessageBox::Show(L"Selecione a API Key!", L"Aviso"); return; }
		workerUrl = L"--API--" + MontarJsonApi();
		modoWorker = 2;              // usa ChamarAgenteMcp (roteia p/ agente_mcp.py)
		payloadWorker = objetivo;
		DefinirOcupado(true, L"Testando a API...");
		workerChat->RunWorkerAsync();
	}

		   // Exporta a conversa/teste atual como um relatorio HTML formatado.
	private: System::Void btnExportarRelatorio_Click(System::Object^ sender, System::EventArgs^ e) {
		if (String::IsNullOrWhiteSpace(rtbChat->Text)) {
			MessageBox::Show(L"Nao ha conteudo para exportar. Faca um teste ou converse primeiro.", L"Aviso");
			return;
		}
		ExportarComoHtml(rtbChat->Text, L"Relatorio de Teste",
			L"Resultado do teste conduzido pela IA", L"relatorio_T2M_");
	}

		   // Funcao compartilhada: gera um HTML formatado e pergunta se quer abrir.
		   // Usada tanto pelo "Relatorio do Teste" (chat) quanto pelo "Exportar Log Tecnico".
	private: void ExportarComoHtml(String^ conteudo, String^ titulo, String^ subtitulo, String^ prefixoArquivo) {
		String^ pasta = Path::Combine(
			Environment::GetFolderPath(Environment::SpecialFolder::MyDocuments), "relatorios T2M");
		Directory::CreateDirectory(pasta);

		String^ dataHora = DateTime::Now.ToString("yyyy-MM-dd_HH-mm-ss");
		String^ caminho = Path::Combine(pasta, prefixoArquivo + dataHora + ".html");

		// Escapa o conteudo para HTML
		String^ corpo = conteudo
			->Replace("&", "&amp;")
			->Replace("<", "&lt;")
			->Replace(">", "&gt;");

		System::Text::StringBuilder^ html = gcnew System::Text::StringBuilder();
		html->Append(L"<!DOCTYPE html>\n<html lang=\"pt-br\">\n<head>\n");
		html->Append(L"<meta charset=\"UTF-8\">\n");
		html->Append(L"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n");
		html->Append(L"<title>" + titulo + L" - T2M Security Manager</title>\n");
		html->Append(L"<style>\n");
		html->Append(L"body{font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f8;color:#222;margin:0;padding:0;}\n");
		html->Append(L".container{max-width:900px;margin:30px auto;background:#fff;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,.08);overflow:hidden;}\n");
		html->Append(L".header{background:#2c3e6b;color:#fff;padding:24px 32px;}\n");
		html->Append(L".header h1{margin:0;font-size:22px;}\n");
		html->Append(L".header .sub{opacity:.85;font-size:13px;margin-top:6px;}\n");
		html->Append(L".meta{padding:16px 32px;background:#eef1f6;font-size:13px;color:#555;border-bottom:1px solid #dde;}\n");
		html->Append(L".content{padding:24px 32px;}\n");
		html->Append(L"pre{white-space:pre-wrap;word-wrap:break-word;font-family:'Consolas','Courier New',monospace;font-size:13px;line-height:1.5;background:#fafbfc;border:1px solid #e3e7ec;border-radius:6px;padding:16px;}\n");
		html->Append(L".footer{padding:16px 32px;font-size:12px;color:#888;border-top:1px solid #eee;text-align:center;}\n");
		html->Append(L"</style>\n</head>\n<body>\n");
		html->Append(L"<div class=\"container\">\n");
		html->Append(L"<div class=\"header\"><h1>" + titulo + L"</h1>");
		html->Append(L"<div class=\"sub\">" + subtitulo + L" - T2M Security Manager</div></div>\n");
		html->Append(L"<div class=\"meta\">");
		html->Append(L"<strong>Data:</strong> " + DateTime::Now.ToString("dd/MM/yyyy HH:mm:ss") + L" &nbsp;|&nbsp; ");
		html->Append(L"<strong>Operador:</strong> " + NomeUsuarioWindows() + L"</div>\n");
		html->Append(L"<div class=\"content\">\n<pre>" + corpo + L"</pre>\n</div>\n");
		html->Append(L"<div class=\"footer\">Gerado automaticamente pelo T2M Security Manager</div>\n");
		html->Append(L"</div>\n</body>\n</html>");

		try {
			File::WriteAllText(caminho, html->ToString(), System::Text::Encoding::UTF8);
			System::Windows::Forms::DialogResult r = MessageBox::Show(
				L"Arquivo salvo em:\n" + caminho + L"\n\nDeseja abrir agora no navegador?",
				L"Exportado", MessageBoxButtons::YesNo, MessageBoxIcon::Information);
			if (r == System::Windows::Forms::DialogResult::Yes) {
				System::Diagnostics::Process::Start(caminho);
			}
		}
		catch (Exception^ ex) {
			MessageBox::Show(L"Erro ao salvar: " + ex->Message, L"Erro");
		}
	}

	private: System::Void btnSaveScript_Click(System::Object^ sender, System::EventArgs^ e) {
		String^ textoCompleto = rtbChat->Text;
		int idxStart = textoCompleto->LastIndexOf("```");
		int offset = 3;

		if (textoCompleto->LastIndexOf("```python") != -1) {
			idxStart = textoCompleto->LastIndexOf("```python");
			offset = 9;
		}
		else if (textoCompleto->LastIndexOf("```robot") != -1) {
			idxStart = textoCompleto->LastIndexOf("```robot");
			offset = 8;
		}
		else if (textoCompleto->LastIndexOf("```sql") != -1) {
			idxStart = textoCompleto->LastIndexOf("```sql");
			offset = 6;
		}

		if (idxStart != -1) {
			int idxEnd = textoCompleto->IndexOf("```", idxStart + offset);
			if (idxEnd != -1) {
				String^ codigo = textoCompleto->Substring(idxStart + offset, idxEnd - (idxStart + offset))->Trim();

				String^ pastaIA = Path::Combine(Environment::GetFolderPath(Environment::SpecialFolder::MyDocuments), "modelos de teste em IA");
				Directory::CreateDirectory(pastaIA);

				String^ ext = ".txt";
				if (textoCompleto->LastIndexOf("```python") != -1) ext = ".py";
				else if (textoCompleto->LastIndexOf("```robot") != -1 || codigo->Contains("*** Settings ***") || codigo->Contains("*** Test Cases ***")) ext = ".robot";
				else if (textoCompleto->LastIndexOf("```sql") != -1 || codigo->StartsWith("SELECT", StringComparison::OrdinalIgnoreCase) || codigo->StartsWith("UPDATE", StringComparison::OrdinalIgnoreCase)) ext = ".sql";

				String^ nomeArq = "script_copilot_" + DateTime::Now.ToString("yyyyMMdd_HHmmss") + ext;
				String^ caminho = Path::Combine(pastaIA, nomeArq);

				File::WriteAllText(caminho, codigo);

				if (!scriptPaths->ContainsKey(nomeArq)) {
					scriptPaths->Add(nomeArq, caminho);
					lstScripts->Items->Add(nomeArq);
				}
				MessageBox::Show(L"Automacao extraida e salva com sucesso:\n" + nomeArq, L"Copilot Integrado");
				formIA->Close();
			}
			else {
				MessageBox::Show(L"A IA nao finalizou o bloco de codigo corretamente.", L"Aviso de Estrutura");
			}
		}
		else {
			MessageBox::Show(L"Nenhum codigo estruturado encontrado na conversa. Peca a IA para gerar o script primeiro!", L"Aviso de Extracao");
		}
	}

	};
}