#include "MyForm.h"

using namespace System;
using namespace System::Windows::Forms;

[STAThreadAttribute]
int main(array<String^>^ args) { // Mudamos de 'void' para 'int'
    Application::EnableVisualStyles();
    Application::SetCompatibleTextRenderingDefault(false);

    // Inicia a janela
    T2MSecurityManager::MyForm form;
    Application::Run(% form);

    return 0; // O Windows exige que retornemos 0 indicando "Sucesso"
}