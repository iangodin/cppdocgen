
namespace TestNamespace
{

int variableX;

void function( int x, double y );

class TestClass
{
public:
    TestClass( void ) = default;

    TestClass( const TestClass &copy ) = default;

    TestClass( TestClass &&move ) = default;
};

}
