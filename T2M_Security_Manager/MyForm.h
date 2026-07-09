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
#using <System.Security.dll>
#using <Microsoft.VisualBasic.dll>


namespace T2MSecurityManager {

	public ref class MyForm : public System::Windows::Forms::Form
	{
	public:
		MyForm(void)
		{
			InitializeComponent();

			// --- BOTÃO GERAR IA ---
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

			// Logo (runtime) + ícone unificado para todas as janelas
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

		// --- Variáveis do Chat Copilot ---
		Form^ formIA;
		RichTextBox^ rtbChat;
		TextBox^ txtChatInput;
		Button^ btnSendChat;
		Button^ btnMapearSite;
		Button^ btnSaveScript;
		ComboBox^ comboModeloChat;

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

		// P/Invoke para liberar handle de ícone gerado a partir de bitmap
		[System::Runtime::InteropServices::DllImport("user32.dll", SetLastError = true)]
			static bool DestroyIcon(System::IntPtr handle);

		// =====================================================================
		// --- HELPERS DE CAMINHO, ÍCONE E CRIPTOGRAFIA ---
		// =====================================================================
	private: String^ CaminhoApp(String^ arquivo) {
		return Path::Combine(Application::StartupPath, arquivo);
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
			return base64; // legado em texto puro: usa como está (será re-cifrado no próximo save)
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
			   this->btnAdd->Text = L"+ Add";
			   this->btnAdd->UseVisualStyleBackColor = false;
			   this->btnAdd->Click += gcnew System::EventHandler(this, &MyForm::btnAdd_Click);

			   this->btnRemove->BackColor = System::Drawing::Color::LightCoral;
			   this->btnRemove->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			   this->btnRemove->Location = System::Drawing::Point(105, 90);
			   this->btnRemove->Name = L"btnRemove";
			   this->btnRemove->Size = System::Drawing::Size(75, 35);
			   this->btnRemove->TabIndex = 3;
			   this->btnRemove->Text = L"Remover";
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
			   this->txtToken->UseSystemPasswordChar = true; // não expõe o JWT na tela
			   this->txtToken->TabIndex = 11;

			   this->btnLoginAuto->BackColor = System::Drawing::Color::Silver;
			   this->btnLoginAuto->Enabled = false;
			   this->btnLoginAuto->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			   this->btnLoginAuto->Font = (gcnew System::Drawing::Font(L"Segoe UI", 8, System::Drawing::FontStyle::Bold));
			   this->btnLoginAuto->Location = System::Drawing::Point(740, 510);
			   this->btnLoginAuto->Name = L"btnLoginAuto";
			   this->btnLoginAuto->Size = System::Drawing::Size(160, 25);
			   this->btnLoginAuto->TabIndex = 10;
			   this->btnLoginAuto->Text = L"🔑 Login Automático";
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
			   this->chkSalvar->Text = L"Salvar configurações ao sair";

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

			   this->btnExport->BackColor = System::Drawing::Color::LightGray;
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

		   // --- FUNÇÕES BÁSICAS DA INTERFACE ---
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
		txtOutput->Clear(); txtOutput->AppendText(">>> INICIANDO LOGIN AUTOMÁTICO...\n");

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
				txtOutput->AppendText("\n>>> ERRO: 'python' não encontrado no PATH.\n");
				return;
			}

			array<System::Byte>^ bytes = System::Text::Encoding::UTF8->GetBytes(urlAlvo);
			pLogin->StandardInput->BaseStream->Write(bytes, 0, bytes->Length);
			pLogin->StandardInput->Close();

			// Login pode levar até ~60s (script espera o usuário logar). Teto de 180s.
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
			else { txtOutput->AppendText("\n>>> AVISO: Token não encontrado.\n"); }
		}
		catch (Exception^ ex) { MessageBox::Show(L"Erro: " + ex->Message); }
		finally {
			pLogin->Close();
			txtUrl->Enabled = true; txtToken->Enabled = true; chkHabilitarLogin->Enabled = true;
			btnLoginAuto->Enabled = true; btnLoginAuto->Text = L"🔑 Login Automático";
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
		else MessageBox::Show(L"A pasta ainda não existe.", L"Aviso");
	}

	private: System::Void btnStart_Click(System::Object^ sender, System::EventArgs^ e) {
		if (lstScripts->SelectedIndex == -1 || txtUrl->Text->Length == 0) { MessageBox::Show(L"Preencha a URL e selecione um script!"); return; }
		String^ caminho = scriptPaths[lstScripts->SelectedItem->ToString()];

		txtOutput->Clear(); txtOutput->AppendText(">>> INICIANDO TESTE DINÂMICO <<<\n");
		ProcessStartInfo^ psi = gcnew ProcessStartInfo();
		psi->FileName = "python";
		// URL vai por argv[1]; TOKEN vai por variável de ambiente (fora da linha de comando)
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
			MessageBox::Show(L"'python' não encontrado no PATH. Instale o Python marcando 'Add to PATH'.", L"Erro");
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
		combo->Items->Add("-------------------------"); combo->Items->Add(L"➕ Adicionar Nova API Key...");
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
				return L"Erro: 'python' não encontrado no PATH. Instale o Python marcando 'Add to PATH'.";
			}

			// linha 1 = chave | linha 2 = url | resto = prompt (pode ser multilinha)
			String^ payload = apiKey + "\n" + url + "\n" + prompt;
			array<System::Byte>^ bytes = System::Text::Encoding::UTF8->GetBytes(payload);
			p->StandardInput->BaseStream->Write(bytes, 0, bytes->Length);
			p->StandardInput->Close();

			if (!p->WaitForExit(120000)) { // teto de 120s: nunca congela para sempre
				try { p->Kill(); }
				catch (...) {}
				return L"Tempo esgotado (120s) aguardando a IA. Verifique a conexão ou a chave.";
			}

			String^ output = p->StandardOutput->ReadToEnd();
			int startIdx = output->IndexOf("CHAT_MSG_INICIO");
			int endIdx = output->IndexOf("CHAT_MSG_FIM");
			if (startIdx != -1 && endIdx != -1) {
				startIdx += 15;
				return output->Substring(startIdx, endIdx - startIdx)->Trim();
			}
			return L"Erro de comunicação com a IA:\n" + output;
		}
		finally {
			p->Close();
		}
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

	private: System::Void comboModeloChat_SelectedIndexChanged(System::Object^ sender, System::EventArgs^ e) {
		if (comboModeloChat->SelectedItem != nullptr && comboModeloChat->SelectedItem->ToString() == L"➕ Adicionar Nova API Key...") {
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
			btnSalvar->Text = L"Salvar Chave";
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
		if (idx >= 0 && comboModeloChat->SelectedItem->ToString() != L"➕ Adicionar Nova API Key..." && comboModeloChat->SelectedItem->ToString() != "-------------------------" && comboModeloChat->SelectedItem->ToString() != L" Nenhuma chave ") {
			if (MessageBox::Show(L"Tem certeza que deseja excluir esta chave?", L"Confirmar Exclusão", MessageBoxButtons::YesNo, MessageBoxIcon::Warning) == System::Windows::Forms::DialogResult::Yes) {
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
					MessageBox::Show(L"Chave excluída!", L"T2M Copilot");
				}
			}
		}
		else {
			MessageBox::Show(L"Selecione uma chave válida para excluir.", L"Aviso");
		}
	}

	private: System::Void btnGerarIA_Click(System::Object^ sender, System::EventArgs^ e) {
		if (txtUrl->Text->Trim() == "") {
			MessageBox::Show(L"Preencha a URL Alvo primeiro para a IA poder analisar o projeto!", L"Aviso");
			return;
		}

		formIA = gcnew Form();
		formIA->Text = L"T2M Copilot - Arquiteto de Automação e Qualidade";
		formIA->Size = System::Drawing::Size(750, 650);
		formIA->StartPosition = FormStartPosition::CenterParent;
		formIA->BackColor = System::Drawing::Color::WhiteSmoke;
		AplicarIcone(formIA);

		formIA->Shown += gcnew System::EventHandler(this, &MyForm::formIA_Shown);

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
		btnRemoverChave->Text = L"🗑️ Excluir";
		btnRemoverChave->Location = System::Drawing::Point(290, 39);
		btnRemoverChave->Size = System::Drawing::Size(80, 27);
		btnRemoverChave->BackColor = System::Drawing::Color::LightCoral;
		btnRemoverChave->FlatStyle = FlatStyle::Flat;
		btnRemoverChave->Click += gcnew System::EventHandler(this, &MyForm::btnRemoverChave_Click);
		formIA->Controls->Add(btnRemoverChave);

		CheckBox^ chkMcp = gcnew CheckBox();
		chkMcp->Name = "chkMcpAtivo";
		chkMcp->Text = L"🤖 Habilitar Escâner de Interface (URL/DOM)";
		chkMcp->Location = System::Drawing::Point(380, 40);
		chkMcp->Size = System::Drawing::Size(340, 25);
		chkMcp->Checked = true;
		chkMcp->Font = gcnew System::Drawing::Font("Segoe UI", 9, System::Drawing::FontStyle::Bold);
		chkMcp->ForeColor = System::Drawing::Color::DarkSlateBlue;
		formIA->Controls->Add(chkMcp);

		rtbChat = gcnew RichTextBox();
		rtbChat->Location = System::Drawing::Point(20, 85);
		rtbChat->Size = System::Drawing::Size(690, 380);
		rtbChat->ReadOnly = true;
		rtbChat->BackColor = System::Drawing::Color::White;
		rtbChat->Font = gcnew System::Drawing::Font("Segoe UI", 10);
		formIA->Controls->Add(rtbChat);

		txtChatInput = gcnew TextBox();
		txtChatInput->Location = System::Drawing::Point(20, 480);
		txtChatInput->Size = System::Drawing::Size(580, 60);
		txtChatInput->Multiline = true;
		txtChatInput->Font = gcnew System::Drawing::Font("Segoe UI", 10);
		formIA->Controls->Add(txtChatInput);

		btnSendChat = gcnew Button();
		btnSendChat->Text = L"Enviar";
		btnSendChat->Location = System::Drawing::Point(610, 480);
		btnSendChat->Size = System::Drawing::Size(100, 60);
		btnSendChat->BackColor = System::Drawing::Color::MediumSeaGreen;
		btnSendChat->ForeColor = System::Drawing::Color::White;
		btnSendChat->FlatStyle = FlatStyle::Flat;
		btnSendChat->Click += gcnew System::EventHandler(this, &MyForm::btnSendChat_Click);
		formIA->Controls->Add(btnSendChat);

		btnSaveScript = gcnew Button();
		btnSaveScript->Text = L"💾 2. Extrair e Salvar Código Final";
		btnSaveScript->Location = System::Drawing::Point(20, 555);
		btnSaveScript->Size = System::Drawing::Size(690, 40);
		btnSaveScript->BackColor = System::Drawing::Color::Indigo;
		btnSaveScript->ForeColor = System::Drawing::Color::White;
		btnSaveScript->FlatStyle = FlatStyle::Flat;
		btnSaveScript->Font = gcnew System::Drawing::Font("Segoe UI", 10, System::Drawing::FontStyle::Bold);
		btnSaveScript->Click += gcnew System::EventHandler(this, &MyForm::btnSaveScript_Click);
		formIA->Controls->Add(btnSaveScript);

		formIA->ShowDialog();
	}

	private: System::Void formIA_Shown(System::Object^ sender, System::EventArgs^ e) {
		String^ apiKey = ObterChaveReal();
		if (apiKey == "") {
			rtbChat->AppendText(L">>> Aviso: Nenhuma API Key selecionada. Selecione uma chave válida e feche/abra esta janela para iniciar.\n");
			return;
		}

		rtbChat->SelectionColor = System::Drawing::Color::Gray;
		rtbChat->AppendText(L">>> Sistema: Inicializando motor de Inteligência Artificial...\n");
		formIA->Cursor = Cursors::WaitCursor;
		btnSendChat->Enabled = false;
		Application::DoEvents();

		CheckBox^ chk = (CheckBox^)formIA->Controls["chkMcpAtivo"];
		String^ comando = L"--INICIAR_NOVO_CHAT--";
		if (chk != nullptr && !chk->Checked) comando += L"MCP_OFF";

		String^ resposta = ChamarAgentePython(apiKey, comando, txtUrl->Text);

		rtbChat->SelectionColor = System::Drawing::Color::DarkGreen;
		rtbChat->AppendText(L"\nT2M Copilot Arquiteto:\n" + resposta + L"\n\n");
		rtbChat->ScrollToCaret();
		btnSendChat->Enabled = true;
		formIA->Cursor = Cursors::Default;
	}

	private: System::Void btnSendChat_Click(System::Object^ sender, System::EventArgs^ e) {
		String^ prompt = txtChatInput->Text->Trim();
		if (prompt == "") return;
		String^ apiKey = ObterChaveReal();
		if (apiKey == "") { MessageBox::Show(L"Selecione a API Key!", L"Aviso"); return; }

		rtbChat->SelectionColor = System::Drawing::Color::DarkBlue;
		rtbChat->AppendText(L"Operador:\n" + prompt + L"\n\n");
		txtChatInput->Clear();

		formIA->Cursor = Cursors::WaitCursor;
		btnSendChat->Enabled = false;
		Application::DoEvents();

		String^ resposta = ChamarAgentePython(apiKey, prompt, txtUrl->Text);

		rtbChat->SelectionColor = System::Drawing::Color::DarkGreen;
		rtbChat->AppendText(L"T2M Copilot Arquiteto:\n" + resposta + L"\n\n");
		rtbChat->ScrollToCaret();

		btnSendChat->Enabled = true;
		formIA->Cursor = Cursors::Default;
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
				MessageBox::Show(L"Automação extraída e salva com sucesso:\n" + nomeArq, L"Copilot Integrado");
				formIA->Close();
			}
			else {
				MessageBox::Show(L"A IA não finalizou o bloco de código corretamente.", L"Aviso de Estrutura");
			}
		}
		else {
			MessageBox::Show(L"Nenhum código estruturado encontrado na conversa. Peça à IA para gerar o script primeiro!", L"Aviso de Extração");
		}
	}

	};
}