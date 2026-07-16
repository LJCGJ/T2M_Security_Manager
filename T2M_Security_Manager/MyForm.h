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
		Button^ btnMapearSite;
		Button^ btnSaveScript;
		ComboBox^ comboModeloChat;

		// Botoes/controles de modo (toggle): so um ativo por vez.
		ComboBox^ cmbAutomacao;  // Dropdown de automacao (Tela / API / Banco) = modo MCP
		Button^ btnChatDom;      // Modo Scan DOM (varredura estatica)
		Button^ btnChatConversa; // Modo Chat (so conversa, padrao)
		Label^ lblChatStatus;    // Indicador "processando..."

		// Modo ativo do chat: 0 = Chat (so conversa), 1 = DOM, 2 = Automacao (dropdown).
		// So um modo fica ligado por vez; o controle ligado fica em destaque.
		int modoAtivo;
		int tipoAutomacao;       // quando modoAtivo==2: 0=Tela, 1=API, 2=Banco

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
			   this->btnExport->Text = L"💾 Exportar Log";
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
			for each (KeyValuePair<String^, String^> pair in scriptPaths) sw->WriteLine(pair.Value);
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
				for each (String ^ arquivo in arquivos) {
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
		SaveFileDialog^ save = gcnew SaveFileDialog(); save->Filter = "Log (*.txt)|*.txt";
		if (save->ShowDialog() == System::Windows::Forms::DialogResult::OK) File::WriteAllText(save->FileName, txtOutput->Text);
	}

	private: void CarregarDropdownAPI(ComboBox^ combo) {
		combo->Items->Clear();
		if (File::Exists(CaminhoApp("api_keys_ia.txt"))) {
			array<String^>^ linhas = File::ReadAllLines(CaminhoApp("api_keys_ia.txt"));
			for each (String ^ linha in linhas) {
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
			for each (String ^ linha in linhas) if (!String::IsNullOrWhiteSpace(linha)) chaves->Add(DesprotegerTexto(linha->Trim()));
			if (idx >= 0 && idx < chaves->Count) return chaves[idx];
		}
		return "";
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
	}

	private: System::Void btnRemoverChave_Click(System::Object^ sender, System::EventArgs^ e) {
		int idx = comboModeloChat->SelectedIndex;
		if (idx >= 0 && comboModeloChat->SelectedItem->ToString() != L"+ Adicionar Nova API Key..." && comboModeloChat->SelectedItem->ToString() != "-------------------------" && comboModeloChat->SelectedItem->ToString() != L" Nenhuma chave ") {
			if (MessageBox::Show(L"Tem certeza que deseja excluir esta chave?", L"Confirmar Exclusao", MessageBoxButtons::YesNo, MessageBoxIcon::Warning) == System::Windows::Forms::DialogResult::Yes) {
				if (File::Exists(CaminhoApp("api_keys_ia.txt"))) {
					array<String^>^ linhas = File::ReadAllLines(CaminhoApp("api_keys_ia.txt"));
					List<String^>^ novasLinhas = gcnew List<String^>();
					int cont = 0;
					for each (String ^ linha in linhas) {
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

		// --- MODO AUTOMACAO (dropdown: Tela / API / Banco) = usa MCP ---
		cmbAutomacao = gcnew ComboBox();
		cmbAutomacao->DropDownStyle = ComboBoxStyle::DropDownList;
		cmbAutomacao->Location = System::Drawing::Point(600, 39);
		cmbAutomacao->Size = System::Drawing::Size(110, 29);
		cmbAutomacao->Font = gcnew System::Drawing::Font("Segoe UI", 8, System::Drawing::FontStyle::Bold);
		cmbAutomacao->Items->Add(L"⚙ Automacao");      // item 0 = titulo/placeholder (nao ativa)
		cmbAutomacao->Items->Add(L"🖥 Teste de Tela");   // item 1 = Tela (funciona)
		cmbAutomacao->Items->Add(L"🔌 Teste de API");    // item 2 = API (em breve)
		cmbAutomacao->Items->Add(L"🗄 Banco de Dados");  // item 3 = Banco (em breve)
		cmbAutomacao->SelectedIndex = 0;
		cmbAutomacao->SelectedIndexChanged += gcnew System::EventHandler(this, &MyForm::cmbAutomacao_Changed);
		formIA->Controls->Add(cmbAutomacao);
		dica->SetToolTip(cmbAutomacao,
			L"AUTOMACAO (via MCP, navegador/execucao real)\n"
			L"Teste de Tela: descreva o teste e a IA executa passo a passo ao vivo.\n"
			L"Teste de API / Banco de Dados: em breve.\n"
			L"ATENCAO: consome MUITO MAIS tokens (~100k+ por tarefa).");

		btnSaveScript = gcnew Button();
		btnSaveScript->Text = L"💾 2. Extrair e Salvar Codigo Final";
		btnSaveScript->Location = System::Drawing::Point(20, 545);
		btnSaveScript->Size = System::Drawing::Size(690, 40);
		btnSaveScript->BackColor = System::Drawing::Color::Indigo;
		btnSaveScript->ForeColor = System::Drawing::Color::White;
		btnSaveScript->FlatStyle = FlatStyle::Flat;
		btnSaveScript->Font = gcnew System::Drawing::Font("Segoe UI", 10, System::Drawing::FontStyle::Bold);
		btnSaveScript->Click += gcnew System::EventHandler(this, &MyForm::btnSaveScript_Click);
		formIA->Controls->Add(btnSaveScript);
		dica->SetToolTip(btnSaveScript,
			L"Extrai o ultimo bloco de codigo da conversa e salva como script (.py/.robot/.sql).");

		// Configura o BackgroundWorker (execucao em thread separada = janela nao congela)
		workerChat = gcnew System::ComponentModel::BackgroundWorker();
		workerChat->DoWork += gcnew System::ComponentModel::DoWorkEventHandler(this, &MyForm::workerChat_DoWork);
		workerChat->RunWorkerCompleted += gcnew System::ComponentModel::RunWorkerCompletedEventHandler(this, &MyForm::workerChat_Completed);

		// Modo inicial: Chat (so conversa). Aplica o destaque visual.
		modoAtivo = 0;
		tipoAutomacao = 0;
		AtualizarBotoesModo();

		formIA->ShowDialog();
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
		cmbAutomacao->BackColor = corOff; cmbAutomacao->ForeColor = System::Drawing::Color::Black;

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
			cmbAutomacao->BackColor = corMcpOn; cmbAutomacao->ForeColor = System::Drawing::Color::White;
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
		cmbAutomacao->SelectedIndex = 0;  // reseta o dropdown para o placeholder
		AtualizarBotoesModo();
	}
	private: System::Void btnModoDom_Click(System::Object^ sender, System::EventArgs^ e) {
		if (workerChat->IsBusy) return;
		modoAtivo = 1;
		cmbAutomacao->SelectedIndex = 0;
		AtualizarBotoesModo();
	}

		   // Dropdown de automacao: item 0=placeholder, 1=Tela (funciona), 2=API, 3=Banco (em breve)
	private: System::Void cmbAutomacao_Changed(System::Object^ sender, System::EventArgs^ e) {
		if (workerChat->IsBusy) { cmbAutomacao->SelectedIndex = 0; return; }
		int idx = cmbAutomacao->SelectedIndex;

		if (idx == 0) {
			// Placeholder: nao ativa automacao. Se estava no modo automacao, volta pro Chat.
			if (modoAtivo == 2) { modoAtivo = 0; AtualizarBotoesModo(); }
			return;
		}
		if (idx == 1) {
			// Teste de Tela - funciona (via MCP)
			modoAtivo = 2; tipoAutomacao = 0;
			AtualizarBotoesModo();
		}
		else if (idx == 2 || idx == 3) {
			// API / Banco: em breve. Avisa e volta o dropdown para o placeholder.
			String^ oque = (idx == 2) ? L"Teste de API" : L"Banco de Dados";
			MessageBox::Show(
				oque + L" estara disponivel em breve.\n\nPor enquanto, use o Teste de Tela "
				L"(automacao ao vivo no navegador) ou os modos Chat e Scan DOM.",
				L"Em breve", MessageBoxButtons::OK, MessageBoxIcon::Information);
			cmbAutomacao->SelectedIndex = 0;
			if (modoAtivo == 2) { modoAtivo = 0; }
			AtualizarBotoesModo();
		}
	}

		   // ==========================================================================
		   // --- EXECUCAO NAO-BLOQUEANTE (BackgroundWorker) ---
		   // ==========================================================================

		   // Habilita/desabilita os controles enquanto o Python roda, e mostra status.
	private: void DefinirOcupado(bool ocupado, String^ msgStatus) {
		btnSendChat->Enabled = !ocupado;
		cmbAutomacao->Enabled = !ocupado;
		btnChatDom->Enabled = !ocupado;
		btnChatConversa->Enabled = !ocupado;
		btnSaveScript->Enabled = !ocupado;
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

		// Modos DOM e MCP exigem URL Alvo
		if ((modoAtivo == 1 || modoAtivo == 2) && String::IsNullOrWhiteSpace(txtUrl->Text)) {
			MessageBox::Show(L"Preencha a URL Alvo na tela principal para usar Scan DOM ou Automacao MCP.", L"Aviso");
			return;
		}

		// Eco da mensagem do usuario
		rtbChat->SelectionColor = System::Drawing::Color::DarkBlue;
		rtbChat->AppendText(NomeUsuarioWindows() + L":\n" + prompt + L"\n\n");
		txtChatInput->Clear();

		// Decide a acao conforme o modo ativo
		if (modoAtivo == 2) {
			// MCP ao vivo: o texto do usuario e o objetivo do teste
			rtbChat->SelectionColor = System::Drawing::Color::DarkSlateBlue;
			rtbChat->AppendText(L">>> Iniciando automacao MCP ao vivo. Uma janela do navegador vai abrir. Aguarde...\n\n");
			RodarWorker(2, prompt, L"Automacao ao vivo em andamento (navegador aberto)...");
		}
		else if (modoAtivo == 1) {
			// Scan DOM: escaneia a pagina e usa o texto como pergunta/contexto.
			// O prefixo --SCAN_DOM-- avisa o Python para ativar o escaner nesta mensagem.
			rtbChat->SelectionColor = System::Drawing::Color::DimGray;
			rtbChat->AppendText(L">>> Escaneando a estrutura de " + txtUrl->Text + L"...\n\n");
			RodarWorker(1, L"--SCAN_DOM--\n" + prompt, L"Escaneando a pagina (DOM)...");
		}
		else {
			// Chat normal (so conversa)
			RodarWorker(0, prompt, L"O agente esta pensando...");
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